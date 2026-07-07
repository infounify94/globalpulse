from abc import ABC, abstractmethod
from typing import Dict, Any, List
from core.models.base_event import BaseEvent

class BaseFeatureStore(ABC):
    """
    Abstract Interface for the Feature Store.
    Responsible for persisting events and their computed features to a relational database (e.g., PostgreSQL).
    """

    @abstractmethod
    def store_event(self, event: BaseEvent):
        """Stores a single event and its features."""
        pass

    @abstractmethod
    def store_events(self, events: List[BaseEvent]):
        """Batch stores multiple events."""
        pass

    @abstractmethod
    def get_event(self, event_id: str) -> BaseEvent:
        """Retrieves an event by its ID."""
        pass
        
    @abstractmethod
    def get_historical_data(self, until_date: Any) -> List[BaseEvent]:
        """
        Retrieves all historical events strictly before the `until_date`.
        Crucial for Walk-Forward Validation to prevent data leakage.
        """
        pass
