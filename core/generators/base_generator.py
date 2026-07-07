from abc import ABC, abstractmethod
from typing import Dict, Any

from core.models.base_event import BaseEvent

class BaseFeatureGenerator(ABC):
    """
    Abstract Base Class for all feature generators.
    Enforces a strict interface where a generator takes an Event and returns a dictionary of features.
    """

    @abstractmethod
    def generate(self, event: BaseEvent) -> Dict[str, float]:
        """
        Generates a set of features for the given event.
        
        Args:
            event (BaseEvent): The event to generate features for.
            
        Returns:
            Dict[str, float]: A dictionary of generated features where keys are feature names 
                              and values are the numerical feature values.
        """
        pass

    @property
    @abstractmethod
    def generator_name(self) -> str:
        """Name of the generator (e.g., 'Astronomy', 'CricketStats')."""
        pass
