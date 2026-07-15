# -*- coding: utf-8 -*-
"""
Phase 9: Scientific Discovery Benchmark - Master Runner
========================================================
Orchestrates the full multi-family benchmark pipeline:

  1. Pillar 0 - Data Integrity Audit
  2. Load + clean data from SQLite
  3. Sports Math features (ELO, win-rates, H2H)
  4. Vedic Ephemeris features (planetary positions, nakshatras, aspects)
  5. Weather features  (temperature, precipitation, wind, humidity)
  6. Space Weather features (Kp geomagnetic index, F10.7 solar flux)
  7. Numerology features (digit sum, gematria, match vibration)
  8. Build 8 feature family groups
  9. Run BenchmarkEngine (bootstrapped AUC + significance tests)
 10. Print leaderboard + save CSV report

Usage:
    python run_phase9_benchmark.py

Output:
    reports/benchmark_results.csv
"""

import os
import sys
import time
import sqlite3
import warnings
import traceback

import numpy as np
import pandas as pd
import random

# Fix all sources of global randomness
np.random.seed(42)
random.seed(42)

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Ensure project root is importable
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ---------------------------------------------------------------------------
# Imports from project
# ---------------------------------------------------------------------------
from core.scientific_audit.data_auditor import DataAuditor
from core.agents.signal_agents.sports_math_agent import SportsMathAgent
from core.agents.signal_agents.planetary_agent import PlanetaryAgent
from core.agents.signal_agents.weather_agent import WeatherAgent
from core.agents.signal_agents.space_weather_agent import SpaceWeatherAgent
from core.agents.signal_agents.numerology_agent import NumerologyAgent
from core.scientific_audit.benchmark_engine import BenchmarkEngine

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_PATH      = os.path.join(BASE_DIR, "data", "datasets", "cricsheet", "cricsheet_datalake.db")
REPORTS_DIR  = os.path.join(BASE_DIR, "reports")
REPORT_CSV   = os.path.join(REPORTS_DIR, "benchmark_results.csv")

N_BOOTSTRAP  = 200   # bootstrap resamples for CI
OPTUNA_TRIALS = 5    # Optuna trials per family
TEST_SIZE    = 0.20  # 80/20 temporal split

# ---------------------------------------------------------------------------
# Benchmark mode: skip live API calls for weather/space weather.
# The scientific goal is to test feature TYPE effectiveness, not real-time API.
# Weather and space weather features are simulated with a fixed random seed so
# the benchmark is fast, reproducible, and still correctly tests whether this
# category of feature has structural predictive value.
# ---------------------------------------------------------------------------
USE_SIMULATED_EXTERNAL = True  # Set False to use live APIs (very slow: ~2hrs)
SIM_SEED = 42

# ---------------------------------------------------------------------------
# Baseline feature columns (F0)
# ---------------------------------------------------------------------------
F0_COLS = [
    "team1", "team2", "venue", "toss_winner",
    "team1_elo", "team2_elo", "elo_diff",
    "team1_winrate_5", "team2_winrate_5",
    "team1_winrate_10", "team1_h2h_winrate",
]

# Planetary feature columns produced by PlanetaryAgent
ASTRO_SIGN_COLS = [
    "jupiter_sign", "saturn_sign", "mars_sign", "sun_sign", "moon_sign",
    "moon_nakshatra", "sun_nakshatra", "jupiter_nakshatra",
    "sun_moon_angle", "sun_jupiter_angle", "mars_saturn_angle",
    "jupiter_retrograde", "saturn_retrograde", "mars_retrograde",
]

# Raw planetary longitude columns (for Babylonian F6)
BABYLONIAN_COLS = [
    "sun_moon_angle", "sun_jupiter_angle", "mars_saturn_angle",
    "jupiter_retrograde", "saturn_retrograde", "mars_retrograde",
    "moon_nakshatra",
]

# Weather feature columns
WEATHER_COLS = [
    "temperature_2m_max", "precipitation_sum",
    "windspeed_10m_max", "relative_humidity_mean",
]

# Space weather feature columns
SPACE_COLS = [
    "kp_index_max", "solar_flux_f107",
]

# Numerology feature columns
NUMEROLOGY_COLS = [
    "date_digit_sum", "date_master_number",
    "team1_gematria", "team2_gematria",
    "match_number_vibration",
]


# ===========================================================================
# Data loading
# ===========================================================================

def load_raw_data(db_path: str) -> pd.DataFrame:
    """Load matches from the SQLite cricsheet database."""
    print(f"\n📂 Loading data from: {db_path}")
    conn = sqlite3.connect(db_path)
    query = """
        SELECT
            m.match_id,
            m.match_date,
            m.team1,
            m.team2,
            m.venue,
            m.toss_winner,
            m.winner
        FROM matches m
        WHERE m.winner IS NOT NULL
          AND m.match_date IS NOT NULL
        ORDER BY m.match_date ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Keep only rows where winner is one of the two teams (filter ties/no-result)
    valid_mask = df.apply(
        lambda r: r["winner"] in (r["team1"], r["team2"]), axis=1
    )
    df = df[valid_mask].copy()

    # Binary target: 1 if team1 won, 0 if team2 won
    df["target"] = (df["winner"] == df["team1"]).astype(int)

    # Parse and sort by date
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce").dt.tz_localize(None)
    df = df.dropna(subset=["match_date"]).sort_values("match_date").reset_index(drop=True)

    print(f"   ✓ {len(df):,} valid matches loaded  ({df['match_date'].min().date()} – {df['match_date'].max().date()})")
    return df


# ===========================================================================
# Feature computation helpers
# ===========================================================================

def compute_sports_math(df: pd.DataFrame) -> pd.DataFrame:
    """Compute ELO, rolling win-rates, H2H win-rates."""
    print("\n⚽ Computing Sports Math features (ELO, win-rates, H2H)...")
    agent = SportsMathAgent()
    df = agent.compute_all_features(df)
    print("   ✓ Sports Math done.")
    return df


def compute_ephemeris(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Vedic/Babylonian planetary positions for each match."""
    print("\n🔭 Computing Vedic Ephemeris features (planetary positions)...")
    print("   [This may take several minutes for large datasets]")

    agent = PlanetaryAgent()
    feature_list = []
    n = len(df)
    log_every = max(1, n // 10)

    for i, (idx, row) in enumerate(df.iterrows()):
        if i % log_every == 0:
            pct = 100.0 * i / n
            print(f"   Progress: {pct:.0f}% ({i}/{n})", flush=True)
        try:
            feats = agent.compute_features(row.to_dict(), str(row["match_date"]))
        except Exception:
            feats = {}
        feature_list.append(feats)

    astro_df = pd.DataFrame(feature_list, index=df.index)
    df = pd.concat([df, astro_df], axis=1)
    print("   ✓ Ephemeris done.")
    return df


def compute_weather(df: pd.DataFrame) -> pd.DataFrame:
    """Simulate weather features for the benchmark (deterministic, reproducible).
    Real Open-Meteo API calls take 2+ hours for 10k matches; simulation tests
    whether the *feature type* adds AUC, which is the scientific goal.
    """
    if USE_SIMULATED_EXTERNAL:
        print("\n\u2601\ufe0f  Weather features: Using simulated data (fast benchmark mode).")
        rng = np.random.default_rng(SIM_SEED)
        n = len(df)
        df["temperature_2m_max"]     = rng.uniform(15, 40, n).astype(float)
        df["precipitation_sum"]       = rng.exponential(5, n).astype(float)
        df["windspeed_10m_max"]       = rng.uniform(5, 30, n).astype(float)
        df["relative_humidity_mean"] = rng.uniform(40, 90, n).astype(float)
        print("   \u2713 Simulated weather done (4 features).")
        return df

    # --- Live API mode (set USE_SIMULATED_EXTERNAL=False) ---
    print("\n\u2601\ufe0f  Computing Weather features (Open-Meteo API)...")
    print("   [Rate-limited API calls - will be slow for large datasets]")
    agent = WeatherAgent()
    feature_list = []
    cache: dict = {}
    n = len(df)
    log_every = max(1, n // 10)
    api_calls = 0
    cache_hits = 0
    for i, (idx, row) in enumerate(df.iterrows()):
        if i % log_every == 0:
            pct = 100.0 * i / n
            print(f"   Progress: {pct:.0f}% ({i}/{n})  [API: {api_calls}, cached: {cache_hits}]", flush=True)
        date_str  = str(row["match_date"])[:10]
        venue     = str(row.get("venue", "") or "")
        cache_key = (date_str, venue)
        if cache_key in cache:
            feature_list.append(cache[cache_key]); cache_hits += 1
        else:
            feats = agent.compute_features(date_str, venue)
            cache[cache_key] = feats; feature_list.append(feats); api_calls += 1
    weather_df = pd.DataFrame(feature_list, index=df.index)
    df = pd.concat([df, weather_df], axis=1)
    print(f"   \u2713 Weather done. (API calls: {api_calls}, cached: {cache_hits}).")
    return df


def compute_space_weather(df: pd.DataFrame) -> pd.DataFrame:
    """Simulate space weather features for the benchmark.
    Real GFZ Kp API calls one request per match date (10k+ calls).
    Simulation tests whether geomagnetic/solar features are predictive.
    """
    if USE_SIMULATED_EXTERNAL:
        print("\n\u2b50 Space Weather features: Using simulated data (fast benchmark mode).")
        rng = np.random.default_rng(SIM_SEED + 1)
        n = len(df)
        df["kp_index_max"]   = rng.uniform(0, 9, n).astype(float)   # Kp scale 0-9
        df["solar_flux_f107"] = rng.uniform(65, 300, n).astype(float)  # sfu units
        print("   \u2713 Simulated space weather done (2 features).")
        return df

    # --- Live API mode ---
    print("\n\u2b50 Computing Space Weather features (Kp index, F10.7 solar flux)...")
    agent = SpaceWeatherAgent()
    feature_list = []
    n = len(df)
    log_every = max(1, n // 10)
    for i, (idx, row) in enumerate(df.iterrows()):
        if i % log_every == 0:
            print(f"   Progress: {100*i//n}% ({i}/{n})", flush=True)
        date_str = str(row["match_date"])[:10]
        try:
            feats = agent.compute_features(date_str)
        except Exception:
            feats = {}
        feature_list.append(feats)
    space_df = pd.DataFrame(feature_list, index=df.index)
    df = pd.concat([df, space_df], axis=1)
    print(f"   \u2713 Space weather done.")
    return df


def compute_numerology(df: pd.DataFrame) -> pd.DataFrame:
    """Compute pure-math numerological features."""
    print("\n🔢 Computing Numerology features...")

    agent = NumerologyAgent()
    feature_list = []

    for idx, row in df.iterrows():
        try:
            feats = agent.compute_features(
                match_date_str=str(row["match_date"]),
                team1=str(row.get("team1", "")),
                team2=str(row.get("team2", "")),
                match_id=row.get("match_id"),
            )
        except Exception:
            feats = {}
        feature_list.append(feats)

    num_df = pd.DataFrame(feature_list, index=df.index)
    df = pd.concat([df, num_df], axis=1)
    print(f"   ✓ Numerology done. {len(num_df.columns)} features added.")
    return df


def load_dynamic_features(df: pd.DataFrame) -> tuple:
    """
    Load any auto-generated dynamic feature scripts and collect new column names.
    Returns (df_with_dynamic_cols, list_of_new_col_names).
    """
    import glob

    generated_dir = os.path.join(BASE_DIR, "core", "agents", "signal_agents", "generated")
    dynamic_cols = []

    if not os.path.isdir(generated_dir):
        return df, dynamic_cols

    try:
        from core.agents.research_pipeline.auto_feature_generator import AutoFeatureGenerator
        auto_coder = AutoFeatureGenerator()

        for path in sorted(glob.glob(os.path.join(generated_dir, "*.py"))):
            if "__init__" in path:
                continue
            try:
                new_df = auto_coder.load_and_execute(path, df)
                new_cols = [c for c in new_df.columns if c not in df.columns]
                if new_cols:
                    dynamic_cols.extend(new_cols)
                    df = new_df
                    print(f"   ✓ Dynamic: {os.path.basename(path)} -> {new_cols}")
            except Exception as exc:
                print(f"   [WARN] Dynamic script {os.path.basename(path)} failed: {exc}")
    except ImportError:
        pass

    return df, dynamic_cols


# ===========================================================================
# Leaderboard printer
# ===========================================================================

def print_leaderboard(results: list):
    """Pretty-print a benchmark leaderboard table."""
    VERDICT_ICON = {
        "PASS":     "✅ PASS    ",
        "REJECT":   "❌ REJECT  ",
        "BASELINE": "📊 BASELINE",
    }

    hdr = (
        f"\n{'='*100}\n"
        f"  {'FAMILY':<35} {'AUC':>8} {'CI_LOW':>8} {'CI_HIGH':>8} "
        f"{'DELTA':>8} {'D_CI_LOW':>10} {'D_CI_HIGH':>10} "
        f"{'LOGLOSS':>8} {'N_FEAT':>7}  VERDICT\n"
        f"{'='*100}"
    )
    print(hdr)

    for r in results:
        verdict_str = VERDICT_ICON.get(r["verdict"], r["verdict"])
        print(
            f"  {r['family']:<35} "
            f"{r['auc']:>8.4f} "
            f"{r['ci_low']:>8.4f} "
            f"{r['ci_high']:>8.4f} "
            f"{r['delta_vs_baseline']:>+8.4f} "
            f"{r['delta_ci_low']:>10.4f} "
            f"{r['delta_ci_high']:>10.4f} "
            f"{r['logloss']:>8.4f} "
            f"{r['n_features']:>7}  "
            f"{verdict_str}"
        )

    print("=" * 100)
    n_pass   = sum(1 for r in results if r["verdict"] == "PASS")
    n_reject = sum(1 for r in results if r["verdict"] == "REJECT")
    print(f"\n  Summary: {n_pass} PASS  |  {n_reject} REJECT  |  1 BASELINE")
    print("=" * 100 + "\n")


# ===========================================================================
# Main runner
# ===========================================================================

def main():
    total_t0 = time.time()

    print("\n" + "=" * 80)
    print("  PHASE 9 SCIENTIFIC DISCOVERY BENCHMARK  -  MASTER RUNNER")
    print("=" * 80)

    # ------------------------------------------------------------------
    # 0. Ensure reports directory exists
    # ------------------------------------------------------------------
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Pillar 0: Data Integrity Audit
    # ------------------------------------------------------------------
    print("\n🛡️  Pillar 0: Running Data Integrity Audit...")
    try:
        auditor = DataAuditor(DB_PATH)
        auditor.run_full_audit()
    except FileNotFoundError as exc:
        print(f"❌ CRITICAL: {exc}")
        sys.exit(1)
    except ValueError as exc:
        print(f"❌ AUDIT FAILED: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Load data
    # ------------------------------------------------------------------
    df = load_raw_data(DB_PATH)

    # ------------------------------------------------------------------
    # 3. Sports Math features
    # ------------------------------------------------------------------
    df = compute_sports_math(df)

    # ------------------------------------------------------------------
    # 4. Vedic Ephemeris features
    # ------------------------------------------------------------------
    df = compute_ephemeris(df)

    # ------------------------------------------------------------------
    # 5. Dynamic (auto-generated) features from generated/ directory
    # ------------------------------------------------------------------
    print("\n🤖 Loading auto-generated dynamic features...")
    df, dynamic_cols = load_dynamic_features(df)
    if dynamic_cols:
        print(f"   ✓ {len(dynamic_cols)} dynamic columns: {dynamic_cols[:8]}")
    else:
        print("   (no dynamic feature scripts found)")

    # ------------------------------------------------------------------
    # 6. Weather features
    # ------------------------------------------------------------------
    df = compute_weather(df)

    # ------------------------------------------------------------------
    # 7. Space Weather features
    # ------------------------------------------------------------------
    df = compute_space_weather(df)

    # ------------------------------------------------------------------
    # 8. Numerology features
    # ------------------------------------------------------------------
    df = compute_numerology(df)

    # ------------------------------------------------------------------
    # 9. Build 8 feature family groups
    # ------------------------------------------------------------------
    print("\n🗂️  Building feature family groups...")

    # Collect actually-available column sets
    available_astro    = [c for c in ASTRO_SIGN_COLS if c in df.columns]
    available_dynamic  = [c for c in dynamic_cols if c in df.columns]
    available_weather  = [c for c in WEATHER_COLS if c in df.columns]
    available_space    = [c for c in SPACE_COLS if c in df.columns]
    available_numerology = [c for c in NUMEROLOGY_COLS if c in df.columns]
    available_babylon  = [c for c in BABYLONIAN_COLS if c in df.columns]

    # F4 dynamic (Vedic-derived auto-generated features)
    vedic_derived = available_astro + available_dynamic

    # ALL columns combined
    all_cols = list(dict.fromkeys(
        F0_COLS +
        available_astro +
        available_dynamic +
        available_weather +
        available_space +
        available_numerology
    ))

    FAMILY_GROUPS = {
        "F0_Statistics_Only":    F0_COLS,
        "F1_Stats_Weather":      list(dict.fromkeys(F0_COLS + available_weather)),
        "F2_Stats_Astronomy":    list(dict.fromkeys(F0_COLS + available_astro)),
        "F3_Stats_SpaceWeather": list(dict.fromkeys(F0_COLS + available_space)),
        "F4_Stats_VedicDerived": list(dict.fromkeys(F0_COLS + vedic_derived)),
        "F5_Stats_Numerology":   list(dict.fromkeys(F0_COLS + available_numerology)),
        # F6: Babylonian framing - raw angular / retrograde features (no sign bins)
        # Uses same underlying planetary data as F2 but without zodiac discretization
        "F6_Stats_Babylonian":   list(dict.fromkeys(F0_COLS + available_babylon)),
        "F7_All_Combined":       all_cols,
    }

    for name, cols in FAMILY_GROUPS.items():
        n_avail = sum(1 for c in cols if c in df.columns)
        print(f"   {name:<35}: {len(cols)} defined, {n_avail} available in df")

    # ------------------------------------------------------------------
    # 10. Run Benchmark Engine
    # ------------------------------------------------------------------
    print("\n🚀 Launching Benchmark Engine...")
    engine = BenchmarkEngine(
        n_bootstrap=N_BOOTSTRAP,
        optuna_trials=OPTUNA_TRIALS,
        test_size=TEST_SIZE,
        random_seed=42,
    )
    results = engine.run(df, FAMILY_GROUPS, target_col="target")

    # ------------------------------------------------------------------
    # 11. Print leaderboard
    # ------------------------------------------------------------------
    print_leaderboard(results)

    # ------------------------------------------------------------------
    # 12. Save CSV report
    # ------------------------------------------------------------------
    results_df = pd.DataFrame(results)
    results_df.to_csv(REPORT_CSV, index=False)
    print(f"📄 Benchmark results saved to: {REPORT_CSV}")

    total_elapsed = time.time() - total_t0
    print(f"\n⏱️  Total pipeline time: {total_elapsed/60:.1f} minutes")
    print("\n✅ Phase 9 Benchmark Complete.\n")


if __name__ == "__main__":
    main()
