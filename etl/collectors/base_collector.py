from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseCollector(ABC):
    """
    Abstract interface for all data collectors.
    A collector is responsible for fetching raw data from an external source,
    checking for updates (idempotency), and saving the raw data locally.
    """

    @abstractmethod
    def collect(self) -> List[str]:
        """
        Executes the collection process.
        Returns a list of local file paths (or raw data identifiers) that were collected or updated.
        """
        pass
        
    @property
    @abstractmethod
    def collector_name(self) -> str:
        """Name of the collector."""
        pass
