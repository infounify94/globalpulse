import pandas as pd
import numpy as np
from sklearn.metrics import log_loss, roc_auc_score

class AblationTester:
    def __init__(self, agent_class, X_train, y_train, X_test, y_test, astrology_features):
        self.agent_class = agent_class
        self.X_train = X_train
        self.y_train = y_train
        self.X_test = X_test
        self.y_test = y_test
        self.astrology_features = [f for f in astrology_features if f in X_train.columns]

    def run_ablation(self):
        print("\n==================================================")
        print("SCIENTIFIC ABLATION TEST (Math vs Math+Astrology)")
        print("==================================================")
        
        # Model A: Baseline (No Astrology)
        print("Training Model A: Sports Math Baseline (NO ASTROLOGY)...")
        X_train_baseline = self.X_train.drop(columns=self.astrology_features)
        X_test_baseline = self.X_test.drop(columns=self.astrology_features)
        
        agent_a = self.agent_class(trials=3) # minimal trials for speed
        agent_a.train(X_train_baseline, self.y_train)
        preds_a = agent_a.predict_proba(X_test_baseline)[:, 1]
        
        auc_a = roc_auc_score(self.y_test, preds_a)
        loss_a = log_loss(self.y_test, preds_a)
        
        # Model B: Full Grandmaster Engine
        print("Training Model B: Full Grandmaster Engine (MATH + ASTROLOGY)...")
        agent_b = self.agent_class(trials=3)
        agent_b.train(self.X_train, self.y_train)
        preds_b = agent_b.predict_proba(self.X_test)[:, 1]
        
        auc_b = roc_auc_score(self.y_test, preds_b)
        loss_b = log_loss(self.y_test, preds_b)
        
        print("\n--- ABLATION RESULTS ---")
        print(f"Model A (Math Only)      -> ROC-AUC: {auc_a:.4f} | LogLoss: {loss_a:.4f}")
        print(f"Model B (Math+Astrology) -> ROC-AUC: {auc_b:.4f} | LogLoss: {loss_b:.4f}")
        
        diff = auc_b - auc_a
        if diff > 0:
            print(f"✅ ASTROLOGY ADDS EDGE: ROC-AUC improved by +{diff:.4f}")
        else:
            print(f"❌ ASTROLOGY FAILED: ROC-AUC dropped by {diff:.4f}")
            
        return agent_b  # return full model for permutation

    def run_permutation_test(self, trained_model, n_iterations=5):
        print("\n==================================================")
        print("PERMUTATION TESTING (Shuffling Astrological Signals)")
        print("==================================================")
        
        # Baseline full prediction
        baseline_preds = trained_model.predict_proba(self.X_test)[:, 1]
        baseline_auc = roc_auc_score(self.y_test, baseline_preds)
        
        feature_drops = {}
        for feature in self.astrology_features:
            drops = []
            for _ in range(n_iterations):
                X_shuffled = self.X_test.copy()
                # Randomly shuffle this column to destroy its real-world timing
                X_shuffled[feature] = np.random.permutation(X_shuffled[feature].values)
                
                shuffled_preds = trained_model.predict_proba(X_shuffled)[:, 1]
                shuffled_auc = roc_auc_score(self.y_test, shuffled_preds)
                drops.append(baseline_auc - shuffled_auc)
                
            avg_drop = np.mean(drops)
            feature_drops[feature] = avg_drop
            
        print("\n--- PERMUTATION RESULTS (Average AUC Drop when shuffled) ---")
        for k, v in sorted(feature_drops.items(), key=lambda item: item[1], reverse=True):
            print(f"{k}: {v:+.5f} AUC")
            
        print("\n(Note: Positive values indicate the feature is real. Values near 0 indicate noise).")
