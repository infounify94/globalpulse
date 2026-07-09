import os
import sqlite3
import pandas as pd
import numpy as np
from core.engine.models.xgboost_trainer import XGBoostTrainer
from core.engine.metrics import ModelMetrics
import json

def run_audit():
    import pandas as pd
    import json
    
    train_df = pd.read_parquet("datasets/train_2008_2023.parquet")
    test_df = pd.read_parquet("datasets/test_2024_2025.parquet")
    
    def extract_features(df):
        features_list = []
        for _, row in df.iterrows():
            row_features = {}
            for col in ['stat_features', 'astro_features', 'env_features', 'vedic_features', 'babylonian_features', 'numerology_features', 'pancha_bhuta_features']:
                if col in row and pd.notna(row[col]) and row[col] not in ('', 'null'):
                    try:
                        feat_dict = json.loads(row[col]) if isinstance(row[col], str) else row[col]
                        if isinstance(feat_dict, dict):
                            row_features.update(feat_dict)
                    except Exception:
                        pass
            features_list.append(row_features)
        X = pd.DataFrame(features_list).fillna(0).apply(pd.to_numeric, errors='coerce').fillna(0)
        
        # Calculate team_a_win
        y = (df['outcome'] == df['team_a_id']).astype(int)
        return X, y
        
    X_train_full, y_train = extract_features(train_df)
    X_test_full, y_test = extract_features(test_df)
    
    # 1. Placebo Feature Test
    print("Running Placebo Feature Test...")
    X_train_placebo = X_train_full.copy()
    X_test_placebo = X_test_full.copy()
    for i in range(1, 21):
        X_train_placebo[f'random_feature_{i}'] = np.random.randn(len(X_train_placebo))
        X_test_placebo[f'random_feature_{i}'] = np.random.randn(len(X_test_placebo))
        
    trainer = XGBoostTrainer(random_seed=42)
    trainer.train(X_train_placebo, y_train)
    importances = trainer.get_feature_importances()
    features = list(X_train_placebo.columns)
    
    feat_imp = pd.DataFrame({'feature': features, 'importance': importances}).sort_values('importance', ascending=False)
    top_20 = feat_imp.head(20)['feature'].tolist()
    randoms_in_top = sum(1 for f in top_20 if 'random_feature' in f)
    
    with open("scientific_audit/placebo_feature_test.md", "w") as f:
        f.write("# Placebo Feature Test\n")
        f.write(f"Random features in Top 20: {randoms_in_top}\n")
        f.write("Status: PASS" if randoms_in_top == 0 else "Status: FAIL")
        
    # 2. Random Label Test
    print("Running Random Label Test...")
    y_train_shuffled = np.random.permutation(y_train)
    trainer.train(X_train_full, y_train_shuffled)
    model = trainer.get_model()
    y_pred_rand = model.predict(X_test_full)
    acc_rand = (y_test == y_pred_rand).mean()
    
    with open("scientific_audit/random_label_test.md", "w") as f:
        f.write("# Random Label Test\n")
        f.write("Expected Accuracy: ~50-60% (Base Rate)\n")
        f.write(f"Actual Accuracy: {acc_rand*100:.2f}%\n")
        f.write("Status: PASS" if 0.40 <= acc_rand <= 0.60 else "Status: FAIL (Model Memorized Labels / Leakage!)")
        
    # 3. Model Robustness (Seeds)
    print("Running Seed Robustness Test...")
    seeds = [42, 123, 456, 789, 999]
    accs = []
    for s in seeds:
        t = XGBoostTrainer(random_seed=s)
        t.train(X_train_full, y_train)
        pred = t.get_model().predict(X_test_full)
        accs.append((y_test == pred).mean())
        
    variance = max(accs) - min(accs)
    
    with open("scientific_audit/robustness_report.md", "w") as f:
        f.write("# Seed Robustness Report\n")
        for s, a in zip(seeds, accs):
            f.write(f"Seed {s}: {a*100:.2f}%\n")
        f.write(f"\nMax Variance: {variance*100:.2f}%\n")
        f.write("Status: PASS" if variance < 0.05 else "Status: FAIL (Model is highly unstable)")

if __name__ == "__main__":
    run_audit()
