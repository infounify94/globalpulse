from abc import ABC, abstractmethod
from typing import List, Any
from core.models.base_event import BaseEvent

class BaseTrainer(ABC):
    """
    Abstract interface for model training, enforcing chronological Walk-Forward Validation.
    """

    def __init__(self, model: Any):
        self.model = model

    @abstractmethod
    def train_walk_forward(self, historical_events: List[BaseEvent], validation_steps: int):
        """
        Executes a strict walk-forward validation.
        
        Args:
            historical_events: List of all events sorted chronologically.
            validation_steps: The number of periods to validate (e.g., each step could be a year or a season).
        
        Raises:
            DataLeakageError if train events occur after test events.
        """
        pass

    def generate_walk_forward_splits(self, start_year: int, end_year: int, step_years: int = 1) -> List[dict]:
        """
        Generates boundaries for walk-forward chronological validation.
        Yields a list of dictionaries containing train_start, train_end, test_start, test_end.
        """
        splits = []
        current_test_start = start_year + step_years
        
        while current_test_start <= end_year:
            # Train from the beginning of recorded time up to the start of the test year
            # Test on the current test year
            splits.append({
                "train_start_year": start_year,
                "train_end_year": current_test_start - 1,
                "test_start_year": current_test_start,
                "test_end_year": current_test_start + step_years - 1
            })
            current_test_start += step_years
            
        return splits

    @abstractmethod
    def get_feature_importance(self) -> dict:
        """Returns the importance of each feature (Gain/Permutation) after training."""
        pass
        
    def _verify_no_leakage(self, train_events: List[BaseEvent], test_events: List[BaseEvent]):
        """
        Core scientific integrity check.
        Ensures max(train_date) < min(test_date).
        """
        if not train_events or not test_events:
            return
            
        max_train = max(e.date for e in train_events)
        min_test = min(e.date for e in test_events)
        
        if max_train >= min_test:
            raise ValueError(f"CRITICAL: Data Leakage Detected. Max train date {max_train} >= Min test date {min_test}")
