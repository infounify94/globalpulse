from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging
import requests

class BaseDataConnector(ABC):
    """
    Generic Data Connector interface.
    Ensures domain independence (Cricket, Football, Stocks).
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        
    @abstractmethod
    def fetch_live_matches(self) -> List[Dict[str, Any]]:
        """Fetches upcoming matches for prediction."""
        pass
        
    @abstractmethod
    def fetch_recent_results(self) -> List[Dict[str, Any]]:
        """Fetches completed match outcomes for continuous learning."""
        pass

class MockCricketConnector(BaseDataConnector):
    """
    Mock implementation simulating a real sports API (e.g. SportMonks).
    """
    def fetch_live_matches(self) -> List[Dict[str, Any]]:
        return [
            {"match_id": "cric_1001", "team_a": "IND", "team_b": "AUS", "date": "2026-10-01", "venue": "MCG"},
            {"match_id": "cric_1002", "team_a": "ENG", "team_b": "NZ", "date": "2026-10-02", "venue": "Lords"}
        ]
        
    def fetch_recent_results(self) -> List[Dict[str, Any]]:
        return [
            {"match_id": "cric_999", "winner": "IND", "score": "320/5"}
        ]

class MockWeatherConnector(BaseDataConnector):
    """Mock implementation simulating OpenWeather."""
    def fetch_live_matches(self) -> List[Dict[str, Any]]: return []
    def fetch_recent_results(self) -> List[Dict[str, Any]]:
        return [{"match_id": "cric_999", "temp": 28.5, "humidity": 65}]

class MockAstronomyConnector(BaseDataConnector):
    """Mock implementation simulating NASA JPL API."""
    def fetch_live_matches(self) -> List[Dict[str, Any]]: return []
    def fetch_recent_results(self) -> List[Dict[str, Any]]:
        return [{"match_id": "cric_999", "moon_phase": "Waxing Gibbous", "mercury_retrograde": False}]
