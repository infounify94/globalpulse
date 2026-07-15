import abc
from typing import List, Dict, Any, Optional

class DataSource(abc.ABC):
    """
    Represents a source of historical truth (e.g. NOAA Kp Index, Wisdom Library text).
    """
    def __init__(self, name: str, source_type: str):
        self.name = name
        self.source_type = source_type
        
    @abc.abstractmethod
    def fetch_data(self, start_date: str, end_date: str) -> Any:
        """Fetch historical data strictly within the date range to prevent leakage."""
        pass


class ResearchAgent(abc.ABC):
    """
    Base class for a domain-specific agent that reads historical data/texts
    and produces a domain understanding that can be used to generate hypotheses.
    """
    def __init__(self, name: str, sources: List[DataSource]):
        self.name = name
        self.sources = sources
        self.knowledge_base = {}

    @abc.abstractmethod
    def ingest_sources(self, up_to_date: str):
        """
        Ingest data from sources strictly prior to `up_to_date`.
        This simulates what the agent would have known historically.
        """
        pass
        
    @abc.abstractmethod
    def generate_domain_summary(self) -> str:
        """
        Produce a summary of the domain knowledge for the HypothesisGenerator.
        """
        pass
