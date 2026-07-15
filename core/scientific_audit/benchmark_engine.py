"""
Phase 9: Scientific Discovery Benchmark Engine.

Tests 8 feature families under identical conditions.
Uses bootstrapped confidence intervals (n=200) to determine statistical significance.

A feature family is only PASS if:
  - AUC improvement over baseline > 0
  - The 95% bootstrapped CI lower bound of delta (AUC_family - AUC_baseline) is > 0
    (improvement is reliably positive, not just noise)

Results dict per family:
  {
    'family'         : str,
    'auc'            : float,
    'ci_low'         : float,   # 2.5th percentile of bootstrapped AUC
    'ci_high'        : float,   # 97.5th percentile of bootstrapped AUC
    'delta_vs_baseline': float, # AUC - baseline_AUC
    'delta_ci_low'   : float,   # 2.5th percentile of bootstrapped delta
    'delta_ci_high'  : float,   # 97.5th percentile of bootstrapped delta
    'logloss'        : float,
    'verdict'        : str,     # 'PASS' | 'REJECT' | 'BASELINE'
    'n_features'     : int,
  }
"""

import os
import sys
import time
import warnings
import numpy as np
import pandas as pd
from typing import Dict, List, Any

# Ensure project root is on path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

warnings.filterwarnings("ignore")


class BenchmarkEngine:
    """
    Orchestrates multi-family feature benchmark with bootstrapped CI testing.

    Parameters
    ----------
    n_bootstrap : int
        Number of bootstrap resamples for CI computation (default 200).
    optuna_trials : int
        Number of Optuna hyperparameter search trials per family (default 3).
    test_size : float
        Fraction of data to hold out as test set (default 0.2).
    random_seed : int
        Reproducibility seed.
    """

    def __init__(
        self,
        n_bootstrap: int = 200,
        optuna_trials: int = 3,
        test_size: float = 0.2,
        random_seed: int = 42,
    ):
        self.n_bootstrap = n_bootstrap
        self.optuna_trials = optuna_trials
        self.test_size = test_size
        self.random_seed = random_seed
        self._rng = np.random.default_rng(random_seed)

    # ------------------------------------------------------------------
    # Core public method
    # ------------------------------------------------------------------

    def run(
        self,
        full_df: pd.DataFrame,
        family_groups: Dict[str, List[str]],
        target_col: str = "target",
    ) -> List[Dict[str, Any]]:
        """
        Run the full benchmark across all feature families.

        Parameters
        ----------
        full_df : pd.DataFrame
            Complete dataset (features + target column). Must be chronologically sorted.
        family_groups : dict
            Mapping of family_name -> list of column names.
        target_col : str
            Name of the binary target column.

        Returns
        -------
        List[dict]
            One result dict per family, sorted by AUC descending.
        """
        from sklearn.metrics import roc_auc_score, log_loss

        print("\n" + "=" * 70)
        print("  PHASE 9 SCIENTIFIC BENCHMARK ENGINE")
        print(f"  Bootstrap resamples: {self.n_bootstrap}  |  Optuna trials: {self.optuna_trials}")
        print("=" * 70)

        # ---------------------------------------------------------------
        # Train/test split (temporal - no shuffling)
        # ---------------------------------------------------------------
        split_idx = int(len(full_df) * (1 - self.test_size))
        train_df = full_df.iloc[:split_idx].copy()
        test_df  = full_df.iloc[split_idx:].copy()

        y_train = train_df[target_col]
        y_test  = test_df[target_col]

        print(f"  Train samples: {len(train_df):,}  |  Test samples: {len(test_df):,}")
        print("=" * 70 + "\n")

        results: List[Dict[str, Any]] = []
        baseline_auc: float = None
        baseline_probas: np.ndarray = None

        # Run families in insertion order; baseline is first key
        family_names = list(family_groups.keys())

        for i, family_name in enumerate(family_names):
            feature_cols = family_groups[family_name]

            # Filter to only columns that exist in the dataframe
            available = [c for c in feature_cols if c in full_df.columns]
            missing   = [c for c in feature_cols if c not in full_df.columns]

            if missing:
                print(f"  [WARN] {family_name}: {len(missing)} columns not found in df, skipping them.")

            if not available:
                print(f"  [SKIP] {family_name}: no available features, skipping.\n")
                continue

            print(f"  [{i+1}/{len(family_names)}] Training: {family_name}  ({len(available)} features)")
            t0 = time.time()

            try:
                X_train = self._prepare_X(train_df, available)
                X_test  = self._prepare_X(test_df,  available)

                from core.agents.super_agent import OptunaCatBoostAgent
                agent = OptunaCatBoostAgent(
                    name=f"bench_{family_name}",
                    trials=self.optuna_trials,
                )
                agent.train(X_train.copy(), y_train.copy())

                probas = agent.predict_proba(X_test.copy())[:, 1]
                auc = float(roc_auc_score(y_test, probas))
                ll  = float(log_loss(y_test, probas))

            except Exception as exc:
                print(f"  [ERROR] {family_name} failed: {exc}\n")
                continue

            # -----------------------------------------------------------
            # Bootstrap CI on AUC
            # -----------------------------------------------------------
            boot_aucs   = self._bootstrap_auc(y_test.values, probas, self.n_bootstrap)
            ci_low  = float(np.percentile(boot_aucs, 2.5))
            ci_high = float(np.percentile(boot_aucs, 97.5))

            # -----------------------------------------------------------
            # Store baseline probas / compute delta vs baseline
            # -----------------------------------------------------------
            if baseline_auc is None:
                # First family is the baseline
                baseline_auc    = auc
                baseline_probas = probas.copy()
                delta    = 0.0
                d_ci_low = 0.0
                d_ci_high = 0.0
                verdict  = "BASELINE"
            else:
                delta = auc - baseline_auc
                boot_deltas = self._bootstrap_delta(
                    y_test.values, probas, baseline_probas, self.n_bootstrap
                )
                d_ci_low  = float(np.percentile(boot_deltas, 2.5))
                d_ci_high = float(np.percentile(boot_deltas, 97.5))

                # PASS only if the entire 95% CI of delta is above 0
                verdict = "PASS" if d_ci_low > 0 else "REJECT"

            elapsed = time.time() - t0
            print(f"         AUC={auc:.4f}  CI=[{ci_low:.4f}, {ci_high:.4f}]  "
                  f"delta={delta:+.4f}  verdict={verdict}  ({elapsed:.1f}s)\n")

            results.append({
                "family":           family_name,
                "auc":              round(auc, 6),
                "ci_low":           round(ci_low, 6),
                "ci_high":          round(ci_high, 6),
                "delta_vs_baseline":round(delta, 6),
                "delta_ci_low":     round(d_ci_low, 6),
                "delta_ci_high":    round(d_ci_high, 6),
                "logloss":          round(ll, 6),
                "verdict":          verdict,
                "n_features":       len(available),
            })

        # Sort by AUC descending (baseline stays readable at top)
        results.sort(key=lambda r: r["auc"], reverse=True)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prepare_X(self, df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
        """
        Prepare feature matrix: fill NaN with median (numeric) or 'UNKNOWN' (categorical).
        Handles both legacy object dtype and pandas StringDtype (pandas >= 1.0).
        Returns a clean copy.
        """
        X = df[cols].copy()
        for col in X.columns:
            # pd.api.types.is_numeric_dtype is the safest cross-version check:
            # object, StringDtype, CategoricalDtype all return False.
            if pd.api.types.is_numeric_dtype(X[col]):
                median_val = X[col].median()
                if isinstance(median_val, float) and np.isnan(median_val):
                    median_val = 0.0
                X[col] = X[col].fillna(median_val)
            else:
                # String / categorical column — fill missing and cast to plain str
                X[col] = X[col].fillna("UNKNOWN").astype(str)
        return X

    def _bootstrap_auc(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        n: int,
    ) -> np.ndarray:
        """
        Bootstrap n AUC values from paired (y_true, y_pred) resamples.
        """
        from sklearn.metrics import roc_auc_score

        boot_aucs = []
        idx_all = np.arange(len(y_true))
        for _ in range(n):
            idx = self._rng.choice(idx_all, size=len(y_true), replace=True)
            yt = y_true[idx]
            yp = y_pred[idx]
            # Need at least one positive and one negative
            if len(np.unique(yt)) < 2:
                continue
            try:
                boot_aucs.append(roc_auc_score(yt, yp))
            except Exception:
                pass

        return np.array(boot_aucs) if boot_aucs else np.array([0.5])

    def _bootstrap_delta(
        self,
        y_true: np.ndarray,
        y_pred_family: np.ndarray,
        y_pred_baseline: np.ndarray,
        n: int,
    ) -> np.ndarray:
        """
        Bootstrap n delta-AUC values (family - baseline) using PAIRED resampling.
        Paired resampling is critical - the same row indices are used for both models
        so differences in sample composition cannot confound the comparison.
        """
        from sklearn.metrics import roc_auc_score

        deltas = []
        idx_all = np.arange(len(y_true))
        for _ in range(n):
            idx = self._rng.choice(idx_all, size=len(y_true), replace=True)
            yt  = y_true[idx]
            yf  = y_pred_family[idx]
            yb  = y_pred_baseline[idx]

            if len(np.unique(yt)) < 2:
                continue

            try:
                auc_f = roc_auc_score(yt, yf)
                auc_b = roc_auc_score(yt, yb)
                deltas.append(auc_f - auc_b)
            except Exception:
                pass

        return np.array(deltas) if deltas else np.array([0.0])


# ---------------------------------------------------------------------------
# Standalone test (tiny synthetic dataset)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    n = 500
    df = pd.DataFrame({
        "match_date": pd.date_range("2015-01-01", periods=n, freq="D"),
        "team1": np.random.choice(["India", "Australia", "England"], n),
        "team2": np.random.choice(["Pakistan", "NZ", "SA"], n),
        "venue": np.random.choice(["Mumbai", "Sydney", "London"], n),
        "toss_winner": np.random.choice(["India", "Pakistan"], n),
        "team1_elo": np.random.normal(1500, 100, n),
        "team2_elo": np.random.normal(1500, 100, n),
        "elo_diff": np.random.normal(0, 150, n),
        "team1_winrate_5": np.random.uniform(0.2, 0.8, n),
        "team2_winrate_5": np.random.uniform(0.2, 0.8, n),
        "team1_winrate_10": np.random.uniform(0.2, 0.8, n),
        "team1_h2h_winrate": np.random.uniform(0.3, 0.7, n),
        "moon_nakshatra": np.random.randint(0, 27, n).astype(float),
        "kp_index_max": np.random.uniform(0, 9, n),
        "date_digit_sum": np.random.randint(1, 30, n).astype(float),
        "target": np.random.randint(0, 2, n),
    })

    engine = BenchmarkEngine(n_bootstrap=20, optuna_trials=1)

    F0 = ["team1", "team2", "venue", "toss_winner", "team1_elo", "team2_elo",
          "elo_diff", "team1_winrate_5", "team2_winrate_5", "team1_winrate_10", "team1_h2h_winrate"]

    families = {
        "F0_Statistics_Only": F0,
        "F1_Stats_Astro": F0 + ["moon_nakshatra"],
        "F2_Stats_Space": F0 + ["kp_index_max"],
        "F3_All_Combined": F0 + ["moon_nakshatra", "kp_index_max", "date_digit_sum"],
    }

    results = engine.run(df, families)
    print("\n=== RESULTS ===")
    for r in results:
        print(r)
