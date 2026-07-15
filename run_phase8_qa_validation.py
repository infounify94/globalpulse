import os
import sys
import glob
import pandas as pd
import sqlite3

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.scientific_audit.data_auditor import DataAuditor
from core.agents.signal_agents.sports_math_agent import SportsMathAgent
from core.agents.signal_agents.planetary_agent import PlanetaryAgent
from core.agents.super_agent import OptunaCatBoostAgent
from core.agents.research_pipeline.auto_feature_generator import AutoFeatureGenerator
from core.scientific_audit.ablation_tester import AblationTester
from core.scientific_audit.financial_backtester import FinancialBacktester

def extract_all_data(db_path):
    print(f"Extracting matches from {db_path}...")
    conn = sqlite3.connect(db_path)
    query = '''
        SELECT m.match_id, m.match_date, m.team1, m.team2, m.venue, m.toss_winner, m.winner
        FROM matches m
        WHERE m.winner IS NOT NULL AND m.match_date IS NOT NULL
        ORDER BY m.match_date ASC
    '''
    df = pd.read_sql_query(query, conn)
    df = df[df['winner'].isin(df['team1']) | df['winner'].isin(df['team2'])].copy()
    df['target'] = (df['winner'] == df['team1']).astype(int)
    
    df['match_date'] = pd.to_datetime(df['match_date'], errors='coerce').dt.tz_localize(None)
    df = df.dropna(subset=['match_date']).sort_values('match_date').reset_index(drop=True)
    return df

def run_phase8_qa():
    db_path = "data/datasets/cricsheet/cricsheet_datalake.db"
    
    auditor = DataAuditor(db_path)
    auditor.run_full_audit()
    
    raw_df = extract_all_data(db_path)
    
    sports_agent = SportsMathAgent()
    df = sports_agent.compute_all_features(raw_df)
    
    print("\n--- Computing Vedic Ephemeris (This takes a moment...) ---")
    planetary_agent = PlanetaryAgent()
    feature_list = []
    interval = max(1, len(df) // 10)
    for idx, row in df.iterrows():
        if idx % interval == 0:
            print(f"  Progress: {(idx/len(df))*100:.0f}%")
        feats = planetary_agent.compute_features(row.to_dict(), str(row['match_date']))
        feature_list.append(feats)
    planetary_df = pd.DataFrame(feature_list, index=df.index)
    df = pd.concat([df, planetary_df], axis=1)

    auto_coder = AutoFeatureGenerator()
    generated_dir = os.path.join(BASE_DIR, "core", "agents", "signal_agents", "generated")
    dynamic_cols = []
    for path in glob.glob(os.path.join(generated_dir, "*.py")):
        if "__init__" in path: continue
        try:
            new_df = auto_coder.load_and_execute(path, df)
            new_cols = [c for c in new_df.columns if c not in df.columns]
            if new_cols:
                dynamic_cols.extend(new_cols)
                df = new_df
        except Exception: pass
        
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    astrology_features = [
        'jupiter_sign', 'saturn_sign', 'mars_sign', 'sun_sign', 'moon_sign',
        'moon_nakshatra', 'sun_nakshatra', 'jupiter_nakshatra',
        'sun_moon_angle', 'sun_jupiter_angle', 'mars_saturn_angle',
        'jupiter_retrograde', 'saturn_retrograde', 'mars_retrograde'
    ] + dynamic_cols
    
    features = [
        'team1', 'team2', 'venue', 'toss_winner',
        'team1_elo', 'team2_elo', 'elo_diff', 'team1_winrate_5', 'team2_winrate_5', 'team1_winrate_10', 'team1_h2h_winrate'
    ] + astrology_features
    
    X_train, y_train = train_df[features], train_df['target']
    X_test, y_test = test_df[features], test_df['target']
    
    # QA Suite 1: Scientific Ablation
    ablation = AblationTester(OptunaCatBoostAgent, X_train, y_train, X_test, y_test, astrology_features)
    trained_full_model = ablation.run_ablation()
    ablation.run_permutation_test(trained_full_model, n_iterations=3)
    
    # QA Suite 2: Financial Backtester
    preds = trained_full_model.predict_proba(X_test)[:, 1]
    backtester = FinancialBacktester(initial_bankroll=10000.0, base_bet=100.0)
    backtester.run_backtest(y_test.values, preds)

if __name__ == "__main__":
    run_phase8_qa()
