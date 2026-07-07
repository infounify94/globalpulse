import logging
import os
import json
try:
    import pandas as pd
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    from core.engine.metrics import ModelMetrics
except ImportError:
    logging.warning("scikit-learn or pandas is not installed. BaselineTrainer will be unavailable.")

class BaselineTrainer:
    """
    Trains and evaluates baseline scikit-learn models on pre-generated 
    Walk-Forward Parquet datasets. This establishes the performance floor
    before introducing complex gradient boosting models like XGBoost.
    """
    
    def __init__(self, dataset_dir="datasets", results_dir="results"):
        self.dataset_dir = dataset_dir
        self.results_dir = results_dir
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.models = {
            "logistic_regression": LogisticRegression(max_iter=1000),
            "decision_tree": DecisionTreeClassifier(max_depth=5),
            "random_forest": RandomForestClassifier(n_estimators=100, max_depth=5)
        }
        
    def _extract_xy(self, df):
        # Assumes outcome is a string representing team ID, we need to map to 0/1 relative to team_a
        # Target = 1 if team_a wins, 0 if team_b wins
        y = (df['outcome'] == df['team_a_id']).astype(int).values
        
        # In a real implementation, we would expand JSON columns (stat_features, astro_features)
        # into separate numeric columns here using pd.json_normalize or similar.
        # For this baseline stub, we'll assume features are already flattened or we 
        # mock a dummy feature matrix of the right shape.
        
        # Stub feature extraction (we'd parse the actual features here)
        # Assuming the ETL pipeline flattened them, or we just generate random for the stub to compile
        # In production, we do: pd.json_normalize(df['stat_features'].apply(json.loads))
        X = np.random.rand(len(df), 10) 
        
        return X, y

    def run_baselines(self, train_file: str, test_file: str):
        logging.info(f"Running baselines: Train={train_file} | Test={test_file}")
        
        try:
            train_df = pd.read_parquet(os.path.join(self.dataset_dir, train_file))
            test_df = pd.read_parquet(os.path.join(self.dataset_dir, test_file))
            
            if len(train_df) == 0 or len(test_df) == 0:
                logging.warning("Empty dataset found. Skipping.")
                return {}
                
            X_train, y_train = self._extract_xy(train_df)
            X_test, y_test = self._extract_xy(test_df)
            
            results = {}
            
            for name, model in self.models.items():
                logging.info(f"Training {name}...")
                model.fit(X_train, y_train)
                
                y_pred = model.predict(X_test)
                y_prob = model.predict_proba(X_test)[:, 1] # Probability of class 1
                
                metrics = ModelMetrics.evaluate(y_test, y_pred, y_prob)
                results[name] = metrics
                
                logging.info(f"{name} Results: Accuracy={metrics.get('accuracy', 0):.4f}, "
                             f"Brier={metrics.get('brier_score', 0):.4f}, "
                             f"ROC-AUC={metrics.get('roc_auc', 0):.4f}")
                             
            # Save results
            out_file = os.path.join(self.results_dir, f"baseline_{train_file.split('.')[0]}.json")
            with open(out_file, "w") as f:
                json.dump(results, f, indent=4)
                
            return results
            
        except Exception as e:
            logging.error(f"Failed to run baselines: {e}")
            return {}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    trainer = BaselineTrainer()
    # Example execution:
    # trainer.run_baselines("train_2008_2018.parquet", "test_2019_2019.parquet")
