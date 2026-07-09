import numpy as np
from typing import Dict, Any
from core.engine.models.base_ml_trainer import BaseMLTrainer

class CatBoostTrainer(BaseMLTrainer):
    """CatBoost implementation of the Universal ML Trainer."""
    
    @property
    def algorithm_name(self) -> str:
        return "catboost"
        
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            "iterations": 200,
            "depth": 5,
            "learning_rate": 0.05,
            "random_seed": self.random_seed,
            "verbose": False
        }
        
    def train(self, X_train: np.ndarray, y_train: np.ndarray, params: Dict[str, Any] = None) -> None:
        try:
            from catboost import CatBoostClassifier
        except ImportError:
            raise ImportError("catboost is not installed. Run 'pip install catboost'.")
            
        final_params = self.get_default_parameters()
        if params:
            final_params.update(params)
            
        self.model = CatBoostClassifier(**final_params)
        self.model.fit(X_train, y_train)
        
    def predict_proba(self, X_test: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model must be trained before calling predict_proba.")
        return self.model.predict_proba(X_test)[:, 1]
        
    def get_feature_importances(self) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model must be trained before calling get_feature_importances.")
        return self.model.get_feature_importance()
