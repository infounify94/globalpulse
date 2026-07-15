import os
import sys
import glob
import pandas as pd
import sqlite3
import numpy as np

# Ensure python can find the core module
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.agents.research_pipeline.llm_provider import OllamaProvider, GeminiProvider
from core.agents.research_pipeline.hypothesis_generator import HypothesisGenerator
from core.agents.research_pipeline.hypothesis_validator import HypothesisValidator
from core.agents.research_pipeline.auto_feature_generator import AutoFeatureGenerator
from core.agents.signal_agents.planetary_agent import PlanetaryAgent
from core.agents.super_agent import CatBoostSuperAgent
from core.agents.research_pipeline.walk_forward_trainer import WalkForwardTrainer

BPHS_TEXT = """
Chapter 3: Planetary Characters and Description.
1-2. O Lord! You have stated the names of the planets. Now please tell me about their characteristics. 
The Sun, Jupiter, and Mars are male. The Moon and Venus are female. Saturn and Mercury are neuter.
3-4. The Sun is malefic. The Moon is benefic. Mars is malefic. Mercury is benefic when associated with benefics, but malefic when associated with malefics. Jupiter and Venus are benefics. Saturn is malefic.
5. If Jupiter is in the same sign as the Sun, it is combust and loses its power.
6. The Moon is strong when waxing. It is weak when waning.
7. Venus and Jupiter are the gurus of demons and gods respectively.
"""

def extract_ipl_data(db_path):
    print(f"Extracting IPL data from {db_path}...")
    conn = sqlite3.connect(db_path)
    query = '''
        SELECT m.match_id, m.match_date, m.team1, m.team2, m.venue, m.toss_winner, m.winner, m.format
        FROM matches m
        WHERE m.winner IS NOT NULL AND m.match_date IS NOT NULL AND m.format = 'ipl'
        ORDER BY m.match_date ASC
    '''
    df = pd.read_sql_query(query, conn)
    
    # Target: 1 if team1 wins, 0 if team2 wins
    df = df[df['winner'].isin(df['team1']) | df['winner'].isin(df['team2'])].copy()
    df['target'] = (df['winner'] == df['team1']).astype(int)
    
    # Drop raw winner
    df = df.drop(columns=['winner', 'format'])
    return df

def generate_hypotheses_and_code():
    print("Generating hypotheses from BPHS via Ollama (Llama 3.2)...")
    try:
        llm = GeminiProvider()
        llm.generate_json("Test", "Test")
    except:
        llm = OllamaProvider(model_name="llama3.2")
        
    generator = HypothesisGenerator(llm_provider=llm, corpus_dir="data/datasets/wisdomlib")
    
    # Strict prompt for local models
    generator.system_prompt += (
        "\n\nCRITICAL: You MUST respond with exactly this JSON format. Do not change the keys.\n"
        "{\n"
        "  \"hypothesis_name\": \"is_jupiter_combust\",\n"
        "  \"description\": \"Jupiter is combust when in the same sign as the Sun.\",\n"
        "  \"python_logic\": \"def extract(doc):\\n    return {'is_jupiter_combust': 1 if doc.get('jupiter_sign') == doc.get('sun_sign') else 0}\",\n"
        "  \"confidence_score\": 0.9\n"
        "}\n"
    )
    
    validator = HypothesisValidator()
    auto_coder = AutoFeatureGenerator()
    
    hypotheses = generator.generate_from_corpus("bphs_full")
    valid_modules = []
    
    # Restrict to 5 valid hypotheses to save time
    for hyp in hypotheses:
        if len(valid_modules) >= 5:
            break
            
        is_valid = validator.validate(hyp)
        if is_valid:
            module_path = auto_coder.write_feature_module(hyp)
            valid_modules.append(module_path)
            
    return valid_modules

def run_phase6():
    db_path = "data/datasets/cricsheet/cricsheet_datalake.db"
    
    # 1. Extract Data
    raw_df = extract_ipl_data(db_path)
    if len(raw_df) == 0:
        print("No IPL matches found! Make sure data ingestion ran.")
        return
        
    # Limit to 300 matches for the very first fast end-to-end run
    raw_df = raw_df.head(300).reset_index(drop=True)
    print(f"Extracted {len(raw_df)} IPL matches for fast backtest.")

    # 2. Ephemeris Baseline
    print("Computing baseline ephemeris (this takes a moment)...")
    planetary_agent = PlanetaryAgent()
    feature_list = []
    for idx, row in raw_df.iterrows():
        feats = planetary_agent.compute_features(row.to_dict(), str(row['match_date']))
        feature_list.append(feats)
    planetary_df = pd.DataFrame(feature_list)
    df = pd.concat([raw_df, planetary_df], axis=1)

    # 3. Generate Code
    module_paths = generate_hypotheses_and_code()
    
    # 4. Inject Dynamic Features
    print(f"Injecting {len(module_paths)} autonomous features into the dataset...")
    auto_coder = AutoFeatureGenerator()
    dynamic_feature_cols = []
    
    # Ensure all previous columns are there
    for path in module_paths:
        try:
            # Load the module and execute it over the dataframe
            # The generated code usually returns the appended dataframe
            new_df = auto_coder.load_and_execute(path, df)
            
            # Find the new column that was added
            new_cols = [c for c in new_df.columns if c not in df.columns]
            if new_cols:
                dynamic_feature_cols.extend(new_cols)
                df = new_df
        except Exception as e:
            print(f"Failed to execute feature {path}: {e}")

    print("Final columns:", df.columns.tolist())

    # 5. Walk-Forward Training
    # We will instantiate CatBoostSuperAgent directly and run a basic temporal split
    print("\n--- PHASE 6: SCIENTIFIC BACKTEST ---")
    
    df['match_date'] = pd.to_datetime(df['match_date'], errors='coerce').dt.tz_localize(None)
    df = df.dropna(subset=['match_date']).sort_values('match_date')
    
    split_idx = int(len(df) * 0.7)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    features = [
        'team1', 'team2', 'venue', 'toss_winner',
        'jupiter_sign', 'saturn_sign', 'mars_sign', 'sun_sign', 'moon_sign',
        'jupiter_retrograde', 'saturn_retrograde', 'mars_retrograde'
    ] + dynamic_feature_cols
    
    X_train, y_train = train_df[features], train_df['target']
    X_test, y_test = test_df[features], test_df['target']
    
    agent = CatBoostSuperAgent()
    print(f"Training CatBoost on {len(X_train)} matches, testing on {len(X_test)} matches...")
    agent.train(X_train, y_train)
    
    # Leaderboard
    from core.scientific_audit.shap_analyzer import SHAPAnalyzer
    print("\n--- SHAP LEADERBOARD ---")
    analyzer = SHAPAnalyzer(agent, X_test)
    analyzer.generate_summary()

if __name__ == "__main__":
    run_phase6()
