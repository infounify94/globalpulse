import threading
from typing import Dict, Any, Callable, Tuple
from datetime import datetime

class FeatureCache:
    """
    In-memory caching layer for expensive feature generators (e.g., Astronomy).
    Keys are based on the combination of date (ignoring time if daily is sufficient) and location.
    Thread-safe implementation for ETL processing.
    """
    
    _cache: Dict[str, Dict[str, float]] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_or_compute(cls, key: str, compute_func: Callable[[], Dict[str, float]]) -> Dict[str, float]:
        """
        Retrieves features from cache if they exist.
        Otherwise, calls the compute function, stores the result, and returns it.
        """
        with cls._lock:
            if key in cls._cache:
                return cls._cache[key]
                
        # Compute outside the lock to avoid blocking other cache hits
        result = compute_func()
        
        with cls._lock:
            # Check again in case another thread computed it
            if key not in cls._cache:
                cls._cache[key] = result
            return cls._cache[key]

    @classmethod
    def generate_key(cls, generator_name: str, date: datetime, location: str) -> str:
        """
        Generates a standardized cache key.
        For astronomy and weather, standardizing to the day level is often sufficient
        for caching across multiple events on the same day.
        """
        date_str = date.strftime("%Y-%m-%d")
        return f"{generator_name}::{date_str}::{location}"
        
    @classmethod
    def clear(cls):
        """Clears the cache (useful for testing)."""
        with cls._lock:
            cls._cache.clear()
