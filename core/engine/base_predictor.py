from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple
from core.models.base_event import BaseEvent

class PredictionResult:
    """Standardized API response for a prediction."""
    def __init__(self, 
                 probability: float, 
                 predicted_class: Any, 
                 confidence: float, 
                 similar_historical_events: List[Tuple[str, float]],
                 feature_contributions: Dict[str, float]):
        self.probability = probability
        self.predicted_class = predicted_class
        self.confidence = confidence # e.g. 0.91 means very confident based on calibration
        self.similar_historical_events = similar_historical_events # Reason / Pattern Memory
        self.feature_contributions = feature_contributions # SHAP local explanation

class BasePredictor(ABC):
    """
    Abstract interface for generating predictions.
    Combines both the Statistical ML Engine and Pattern Discovery Engine.
    """

    @abstractmethod
    def predict(self, future_event: BaseEvent) -> PredictionResult:
        """
        Generates a full explainable prediction for a future event.
        Must utilize both ML models and Vector Memory similarity search.
        """
        pass
