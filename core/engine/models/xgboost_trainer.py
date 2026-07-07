import numpy as np
from typing import Dict, Any
from core.engine.models.base_ml_trainer import BaseMLTrainer

class XGBoostTrainer(BaseMLTrainer):
    """XGBoost implementation of the Universal ML Trainer."""
    
    @property
    def algorithm_name(self) -> str:
        return "xgboost"
        
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "eval_metric": "logloss",
            "random_state": self.random_seed
        }
        
    def train(self, X_train: np.ndarray, y_train: np.ndarray, params: Dict[str, Any] = None) -> None:
        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError("xgboost is not installed. Run 'pip install xgboost'.")
            
        final_params = self.get_default_parameters()
        if params:
            final_params.update(params)
            
        self.model = xgb.XGBClassifier(**final_params)
        self.model.fit(X_train, y_train)
        
    def predict_proba(self, X_test: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model must be trained before calling predict_proba.")
        return self.model.predict_proba(X_test)[:, 1]
        
    def get_feature_importances(self) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model must be trained before calling get_feature_importances.")
        return self.model.feature_importances_
