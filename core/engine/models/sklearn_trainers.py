import numpy as np
from typing import Dict, Any
from core.engine.models.base_ml_trainer import BaseMLTrainer

class LogisticRegressionTrainer(BaseMLTrainer):
    @property
    def algorithm_name(self) -> str:
        return "logistic_regression"
        
    def get_default_parameters(self) -> Dict[str, Any]:
        return {"max_iter": 1000, "random_state": self.random_seed}
        
    def train(self, X_train: np.ndarray, y_train: np.ndarray, params: Dict[str, Any] = None) -> None:
        from sklearn.linear_model import LogisticRegression
        final_params = self.get_default_parameters()
        if params: final_params.update(params)
        self.model = LogisticRegression(**final_params)
        self.model.fit(X_train, y_train)
        
    def predict_proba(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X_test)[:, 1]
        
    def get_feature_importances(self) -> np.ndarray:
        return np.abs(self.model.coef_[0])

class RandomForestTrainer(BaseMLTrainer):
    @property
    def algorithm_name(self) -> str:
        return "random_forest"
        
    def get_default_parameters(self) -> Dict[str, Any]:
        return {"n_estimators": 100, "max_depth": 5, "random_state": self.random_seed}
        
    def train(self, X_train: np.ndarray, y_train: np.ndarray, params: Dict[str, Any] = None) -> None:
        from sklearn.ensemble import RandomForestClassifier
        final_params = self.get_default_parameters()
        if params: final_params.update(params)
        self.model = RandomForestClassifier(**final_params)
        self.model.fit(X_train, y_train)
        
    def predict_proba(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X_test)[:, 1]
        
    def get_feature_importances(self) -> np.ndarray:
        return self.model.feature_importances_
