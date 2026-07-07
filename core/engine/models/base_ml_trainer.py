from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import numpy as np

class BaseMLTrainer(ABC):
    """
    Universal interface for all Machine Learning algorithms used in the platform.
    Ensures that XGBoost, LightGBM, Random Forest, etc. all plug into the pipeline identically.
    """
    
    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed
        self.model = None

    @property
    @abstractmethod
    def algorithm_name(self) -> str:
        """Returns the name of the algorithm (e.g., 'xgboost', 'logistic_regression')."""
        pass

    @abstractmethod
    def get_default_parameters(self) -> Dict[str, Any]:
        """Returns robust default hyperparameters for the algorithm."""
        pass

    @abstractmethod
    def train(self, X_train: np.ndarray, y_train: np.ndarray, params: Dict[str, Any] = None) -> None:
        """Fits the underlying model to the training data."""
        pass

    @abstractmethod
    def predict_proba(self, X_test: np.ndarray) -> np.ndarray:
        """
        Returns the raw predicted probabilities for the positive class (class 1).
        This output will subsequently be passed to the Calibration Layer.
        """
        pass

    @abstractmethod
    def get_feature_importances(self) -> np.ndarray:
        """
        Returns native feature importances (e.g., Gini, Gain, Weights) 
        before SHAP is applied. Useful as a baseline fallback.
        """
        pass
        
    def get_model(self) -> Any:
        """Returns the raw underlying model object (needed for SHAP and Calibration)."""
        if self.model is None:
            raise ValueError(f"Model {self.algorithm_name} has not been trained yet.")
        return self.model
