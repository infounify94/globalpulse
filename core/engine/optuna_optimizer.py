import optuna
import logging
import numpy as np
from typing import Any, Dict
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import log_loss

class OptunaOptimizer:
    """
    Automated Hyperparameter Tuning engine using Optuna.
    Respects time-series nature of data during internal CV.
    """
    
    def __init__(self, algorithm_name: str, n_trials: int = 50):
        self.algorithm_name = algorithm_name
        self.n_trials = n_trials
        
    def _objective(self, trial: optuna.Trial, X: np.ndarray, y: np.ndarray) -> float:
        """
        Defines the hyperparameter search space and evaluation metric.
        """
        # 1. Define hyperparameter search space based on algorithm
        if self.algorithm_name == "xgboost":
            from xgboost import XGBClassifier
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                "random_state": 42
            }
            model = XGBClassifier(**params)
        elif self.algorithm_name == "lightgbm":
            from lightgbm import LGBMClassifier
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
                "num_leaves": trial.suggest_int("num_leaves", 20, 100),
                "random_state": 42
            }
            model = LGBMClassifier(**params)
        else:
            # Fallback for baseline models like LogisticRegression
            from sklearn.linear_model import LogisticRegression
            params = {
                "C": trial.suggest_float("C", 1e-4, 10.0, log=True),
                "max_iter": 1000
            }
            model = LogisticRegression(**params)
            
        # 2. TimeSeriesSplit to prevent leakage during internal cross-validation
        tscv = TimeSeriesSplit(n_splits=3)
        scores = []
        
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr, y_val = y[train_idx], y[val_idx]
            
            model.fit(X_tr, y_tr)
            preds = model.predict_proba(X_val)
            
            # We optimize for Log Loss (or Brier score)
            loss = log_loss(y_val, preds)
            scores.append(loss)
            
        return float(np.mean(scores))
        
    def optimize(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict[str, Any]:
        """
        Runs the Optuna study and returns the best hyperparameters.
        """
        logging.info(f"Starting Optuna Optimization for {self.algorithm_name} ({self.n_trials} trials)")
        # Silence optuna logging for clean stdout
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        
        study = optuna.create_study(direction="minimize")
        study.optimize(lambda trial: self._objective(trial, X_train, y_train), n_trials=self.n_trials)
        
        best_params = study.best_params
        best_value = study.best_value
        
        logging.info(f"Optimization complete. Best LogLoss: {best_value:.4f}")
        return best_params
