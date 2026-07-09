import os
import logging
import json
from abc import ABC, abstractmethod
import requests

logger = logging.getLogger(__name__)

class MatchProvider(ABC):
    @abstractmethod
    def fetch_upcoming_matches(self):
        """Returns a list of upcoming matches in a standard format."""
        pass

class CricAPIProvider(MatchProvider):
    def __init__(self):
        self.api_key = os.environ.get("CRICAPI_KEY")
        self.base_url = "https://api.cricapi.com/v1/matches"
        
    def fetch_upcoming_matches(self):
        if not self.api_key:
            raise ValueError("CRICAPI_KEY not set")
        
        try:
            # Short timeout to prevent hanging the backend
            resp = requests.get(
                f"{self.base_url}?apikey={self.api_key}&offset=0",
                timeout=3
            )
            resp.raise_for_status()
            data = resp.json()
            matches = data.get("data", [])
            # Filter for upcoming matches only
            upcoming = [m for m in matches if m.get("matchStarted") is False]
            return upcoming
        except Exception as e:
            logger.error(f"CricAPI failed: {e}")
            raise

class SportMonksProvider(MatchProvider):
    def __init__(self):
        self.api_key = os.environ.get("SPORTMONKS_KEY")
        
    def fetch_upcoming_matches(self):
        if not self.api_key:
            raise ValueError("SPORTMONKS_KEY not set")
        # Implementation placeholder
        raise NotImplementedError("SportMonks provider not fully implemented")

class CSVProvider(MatchProvider):
    def fetch_upcoming_matches(self):
        csv_path = "data/upcoming_matches.csv"
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"{csv_path} not found")
        # Implementation placeholder - usually reads CSV and maps to standard dict
        raise NotImplementedError("CSV provider not fully implemented")

class MockProvider(MatchProvider):
    def fetch_upcoming_matches(self):
        logger.info("Using MockProvider for upcoming matches")
        # Return a standard mock upcoming match
        return [
            {
                "id": "mock-123",
                "name": "India vs Australia, 1st ODI",
                "matchType": "odi",
                "status": "Upcoming",
                "venue": "Wankhede Stadium, Mumbai",
                "date": "2026-08-15T14:00:00Z",
                "dateTimeGMT": "2026-08-15T14:00:00Z",
                "teams": ["India", "Australia"],
                "teamInfo": [
                    {"name": "India", "shortname": "IND"},
                    {"name": "Australia", "shortname": "AUS"}
                ]
            }
        ]

class ProviderChain:
    """Chain of responsibility for match providers."""
    def __init__(self):
        self.providers = [
            CricAPIProvider(),
            SportMonksProvider(),
            CSVProvider(),
            MockProvider()
        ]
        
    def fetch_upcoming_matches(self):
        for provider in self.providers:
            try:
                matches = provider.fetch_upcoming_matches()
                if matches is not None:
                    logger.info(f"Successfully fetched {len(matches)} matches via {provider.__class__.__name__}")
                    return matches
            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} failed: {e}")
                continue
                
        # Fallback if somehow even MockProvider fails
        logger.error("All MatchProviders failed!")
        return []
