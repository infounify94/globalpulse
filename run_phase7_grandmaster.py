import os
import sys
import glob
import pandas as pd
import sqlite3
import numpy as np

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.scientific_audit.data_auditor import DataAuditor
from core.agents.signal_agents.sports_math_agent import SportsMathAgent
from core.agents.signal_agents.planetary_agent import PlanetaryAgent
from core.agents.super_agent import OptunaCatBoostAgent
from core.agents.research_pipeline.auto_feature_generator import AutoFeatureGenerator
from core.scientific_audit.shap_analyzer import SHAPAnalyzer

def extract_all_data(db_path):
    print(f"Extracting all matches from {db_path}...")
    conn = sqlite3.connect(db_path)
    query = '''
        SELECT m.match_id, m.match_date, m.team1, m.team2, m.venue, m.toss_winner, m.winner
        FROM matches m
        WHERE m.winner IS NOT NULL AND m.match_date IS NOT NULL
        ORDER BY m.match_date ASC
    '''
    df = pd.read_sql_query(query, conn)
    
    # Filter for matches that have a winner out of team1/team2 (drops no-results/draws)
    df = df[df['winner'].isin(df['team1']) | df['winner'].isin(df['team2'])].copy()
    df['target'] = (df['winner'] == df['team1']).astype(int)
    # DO NOT DROP WINNER HERE! SportsMathAgent needs it.
    
    df['match_date'] = pd.to_datetime(df['match_date'], errors='coerce').dt.tz_localize(None)
    df = df.dropna(subset=['match_date']).sort_values('match_date').reset_index(drop=True)
    return df

def run_grandmaster_engine():
    db_path = "data/datasets/cricsheet/cricsheet_datalake.db"
    
    # Pillar 0: Guardian Audit
    auditor = DataAuditor(db_path)
    auditor.run_full_audit()
    
    # Extraction
    raw_df = extract_all_data(db_path)
    print(f"\nProceeding with {len(raw_df)} pristine matches.")

    # Pillar 1: Sports Math (ELO, Momentum, H2H)
    print("\n--- PILLAR 1: Computing Dynamic Sports Math ---")
    sports_agent = SportsMathAgent()
    df = sports_agent.compute_all_features(raw_df)
    
    # Pillar 2: Hyper-Advanced Vedic Ephemeris
    print("\n--- PILLAR 2: Computing Vedic Ephemeris (Nakshatras & Aspects) ---")
    planetary_agent = PlanetaryAgent()
    feature_list = []
    total = len(df)
    
    # Print progress every 10%
    interval = max(1, total // 10)
    
    for idx, row in df.iterrows():
        if idx % interval == 0:
            print(f"  Ephemeris progress: {idx}/{total} ({(idx/total)*100:.0f}%)")
        feats = planetary_agent.compute_features(row.to_dict(), str(row['match_date']))
        feature_list.append(feats)
        
    planetary_df = pd.DataFrame(feature_list, index=df.index)
    df = pd.concat([df, planetary_df], axis=1)

    # Pillar 3: Injecting Autonomous Hypotheses (from generated/)
    print("\n--- PILLAR 3: Injecting Autonomous Hypotheses ---")
    auto_coder = AutoFeatureGenerator()
    generated_dir = os.path.join(BASE_DIR, "core", "agents", "signal_agents", "generated")
    dynamic_cols = []
    
    for path in glob.glob(os.path.join(generated_dir, "*.py")):
        if "__init__" in path:
            continue
        try:
            print(f"  Injecting logic from: {os.path.basename(path)}")
            new_df = auto_coder.load_and_execute(path, df)
            new_cols = [c for c in new_df.columns if c not in df.columns]
            if new_cols:
                dynamic_cols.extend(new_cols)
                df = new_df
        except Exception as e:
            print(f"Failed to execute feature {path}: {e}")

    # Pillar 4: Optuna Meta-Ensemble & Walk-Forward
    print("\n--- PILLAR 4: Walk-Forward Training with Optuna Meta-Ensemble ---")
    
    # We will do a simple Train-Test split for this monumental run to save time, 
    # instead of a full sliding window (which would take hours with Optuna).
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    features = [
        'team1', 'team2', 'venue', 'toss_winner',
        'team1_elo', 'team2_elo', 'elo_diff', 'team1_winrate_5', 'team2_winrate_5', 'team1_winrate_10', 'team1_h2h_winrate',
        'jupiter_sign', 'saturn_sign', 'mars_sign', 'sun_sign', 'moon_sign',
        'moon_nakshatra', 'sun_nakshatra', 'jupiter_nakshatra',
        'sun_moon_angle', 'sun_jupiter_angle', 'mars_saturn_angle',
        'jupiter_retrograde', 'saturn_retrograde', 'mars_retrograde'
    ] + dynamic_cols
    
    X_train, y_train = train_df[features], train_df['target']
    X_test, y_test = test_df[features], test_df['target']
    
    # We limit Optuna trials to 5 for speed during this demonstration run
    agent = OptunaCatBoostAgent(trials=5)
    print(f"Training Optuna-CatBoost on {len(X_train)} matches, testing on {len(X_test)} matches...")
    agent.train(X_train, y_train)
    
    # Final Metrics
    print("\n==================================================")
    print("GRANDMASTER LEADERBOARD (SHAP IMPORTANCE)")
    print("==================================================")
    analyzer = SHAPAnalyzer(agent, X_test)
    analyzer.generate_summary()
    
    # Also calculate basic logloss
    from sklearn.metrics import log_loss, roc_auc_score
    preds = agent.predict_proba(X_test)[:, 1]
    print(f"\nFinal Test LogLoss: {log_loss(y_test, preds):.4f}")
    print(f"Final Test ROC-AUC: {roc_auc_score(y_test, preds):.4f}")

if __name__ == "__main__":
    run_grandmaster_engine()
