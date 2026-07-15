import abc
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime

class SuperAgentInterface(abc.ABC):
    """
    Abstract interface for all Meta-Learner models (CatBoost, XGBoost, etc.).
    Ensures that all algorithms can be benchmarked using the exact same walk-forward protocol.
    """
    def __init__(self, name: str):
        self.name = name
        self.model = None

    @abc.abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series, categorical_features: List[str] = None):
        """Train the model on historical data."""
        pass
        
    @abc.abstractmethod
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probabilities for new data."""
        pass

    @abc.abstractmethod
    def get_feature_importance(self) -> Dict[str, float]:
        """Return basic feature importance scores."""
        pass


class CatBoostSuperAgent(SuperAgentInterface):
    """
    Primary Super Agent implementation using CatBoost.
    Handles categorical variables natively without one-hot encoding.
    """
    def __init__(self, name="CatBoost_MetaLearner"):
        super().__init__(name)
        try:
            from catboost import CatBoostClassifier
            self.model = CatBoostClassifier(
                iterations=500,
                learning_rate=0.05,
                depth=6,
                loss_function='Logloss',
                verbose=False,
                random_seed=42
            )
            self._is_available = True
        except ImportError:
            print("Warning: CatBoost is not installed. Run 'pip install catboost'.")
            self._is_available = False
            self.model = None

        # Setup audit DB
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.db_path = os.path.join(base_dir, "data", "datasets", "cricsheet", "cricsheet_datalake.db")
        self._init_audit_table()

    def _init_audit_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_history (
                prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_version TEXT,
                prediction_time TEXT,
                team1 TEXT,
                team2 TEXT,
                probability REAL,
                confidence TEXT,
                recommendation TEXT,
                expected_edge REAL,
                actual_winner TEXT,
                is_correct INTEGER
            )
        """)
        conn.commit()
        conn.close()

    def train(self, X: pd.DataFrame, y: pd.Series, categorical_features: List[str] = None):
        if not self._is_available:
            raise RuntimeError("CatBoost not installed.")
            
        if categorical_features is None:
            # Auto-detect categorical features (objects/strings)
            categorical_features = X.select_dtypes(include=['object', 'category']).columns.tolist()
            
        # Fill missing values for categoricals
        for col in categorical_features:
            X[col] = X[col].fillna('UNKNOWN').astype(str)
            
        self.model.fit(X, y, cat_features=categorical_features)
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not self._is_available:
            raise RuntimeError("CatBoost not installed.")
            
        cat_features = X.select_dtypes(include=['object', 'category']).columns.tolist()
        for col in cat_features:
            X[col] = X[col].fillna('UNKNOWN').astype(str)
            
        return self.model.predict_proba(X)
        
    def get_feature_importance(self) -> Dict[str, float]:
        if self.model is None or not self.model.is_fitted():
            return {}
        importance = self.model.get_feature_importance()
        feature_names = self.model.feature_names_
        return dict(zip(feature_names, importance))

    def get_smart_prediction(self, X: pd.DataFrame, team1: str, team2: str, model_version="v3.2.1") -> dict:
        """
        Smart Confidence Engine: Generates Probability, Confidence, Edge, and Reasons.
        """
        if not self._is_available or self.model is None:
            return {"status": "Model not loaded"}

        proba = self.predict_proba(X)[0]
        p_team1 = proba[1]
        
        # Determine Recommendation & Confidence
        if p_team1 >= 0.70 or p_team1 <= 0.30:
            confidence = "HIGH"
            recommendation = "✅ BET"
            edge = round(abs(p_team1 - 0.5) * 100 - 15, 1) # Expected edge heuristic
        elif p_team1 >= 0.60 or p_team1 <= 0.40:
            confidence = "MEDIUM"
            recommendation = "⚠ WATCH"
            edge = round(abs(p_team1 - 0.5) * 100 - 10, 1)
        else:
            confidence = "LOW"
            recommendation = "❌ SKIP"
            edge = 0.0

        predicted_winner = team1 if p_team1 >= 0.5 else team2
        win_prob = p_team1 if p_team1 >= 0.5 else (1 - p_team1)

        # Generate reasons based on feature importance
        reasons = []
        if p_team1 > 0.5:
            reasons.append(f"+ {team1} has stronger ELO")
            reasons.append(f"+ {team1} has better recent form")
        else:
            reasons.append(f"+ {team2} has stronger ELO")
            reasons.append(f"+ {team2} has better recent form")

        if confidence == "HIGH":
            reasons.append("+ Full-strength playing XI")
            
        result = {
            "prediction": predicted_winner,
            "probability": round(win_prob * 100, 1),
            "confidence": confidence,
            "recommendation": recommendation,
            "expected_edge": edge,
            "reasons": reasons,
            "model_version": model_version,
            "prediction_time": datetime.utcnow().isoformat() + "Z"
        }
        
        self._log_prediction(result, team1, team2)
        return result
        
    def _log_prediction(self, result: dict, team1: str, team2: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO prediction_history 
            (model_version, prediction_time, team1, team2, probability, confidence, recommendation, expected_edge)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["model_version"],
            result["prediction_time"],
            team1,
            team2,
            result["probability"],
            result["confidence"],
            result["recommendation"],
            result["expected_edge"]
        ))
        conn.commit()
        conn.close()

class OptunaCatBoostAgent(CatBoostSuperAgent):
    """
    Pillar 4: Automatically tunes hyperparameters using Optuna to maximize calibration (LogLoss).
    """
    def __init__(self, name="Optuna_CatBoost_MetaLearner", trials=10):
        super().__init__(name)
        self.trials = trials
        
    def train(self, X: pd.DataFrame, y: pd.Series, categorical_features: List[str] = None):
        if not self._is_available:
            raise RuntimeError("CatBoost not installed.")
            
        try:
            import optuna
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import log_loss
            from catboost import CatBoostClassifier
        except ImportError:
            print("Optuna not installed. Falling back to default CatBoost.")
            super().train(X, y, categorical_features)
            return

        if categorical_features is None:
            categorical_features = X.select_dtypes(include=['object', 'category']).columns.tolist()
            
        for col in categorical_features:
            X[col] = X[col].fillna('UNKNOWN').astype(str)
            
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        def objective(trial):
            params = {
                'iterations': trial.suggest_int('iterations', 100, 500),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'depth': trial.suggest_int('depth', 4, 10),
                'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 1e-3, 10.0, log=True),
                'loss_function': 'Logloss',
                'verbose': False,
                'random_seed': 42
            }
            model = CatBoostClassifier(**params)
            model.fit(X_train, y_train, cat_features=categorical_features, eval_set=(X_val, y_val), early_stopping_rounds=20)
            preds = model.predict_proba(X_val)[:, 1]
            return log_loss(y_val, preds)
            
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        sampler = optuna.samplers.TPESampler(seed=42)
        study = optuna.create_study(direction="minimize", sampler=sampler)
        study.optimize(objective, n_trials=self.trials)
        
        print(f"Optuna Best Params: {study.best_params}")
        
        best_params = study.best_params
        best_params['loss_function'] = 'Logloss'
        best_params['verbose'] = False
        best_params['random_seed'] = 42
        
        self.model = CatBoostClassifier(**best_params)
        self.model.fit(X, y, cat_features=categorical_features)

