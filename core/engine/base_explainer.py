from abc import ABC, abstractmethod
from typing import Dict, Any
from core.models.base_event import BaseEvent

class BaseExplainer(ABC):
    """
    Abstract interface for Explainable AI (XAI).
    Responsible for generating SHAP values and explaining individual predictions.
    """

    @abstractmethod
    def fit_explainer(self, model: Any, background_data: Any):
        """Fits the SHAP explainer on the trained model and historical background data."""
        pass

    @abstractmethod
    def explain_prediction(self, event: BaseEvent) -> Dict[str, float]:
        """
        Returns local feature contributions (e.g., SHAP values) for a specific event.
        Answers: 'Why did the model make this specific prediction?'
        """
        pass
