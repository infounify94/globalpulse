import os
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random

class BaseLiveProvider(ABC):
    @abstractmethod
    def fetch_upcoming_matches(self, days_ahead: int = 7) -> List[Dict]:
        """Fetch matches starting within the next `days_ahead` days."""
        pass
        
    @abstractmethod
    def fetch_match_result(self, match_id: str) -> Optional[str]:
        """Fetch the winner of a completed match. Returns None if incomplete/draw."""
        pass


class MockProvider(BaseLiveProvider):
    """Generates fake upcoming matches for testing the Shadow Daemon architecture."""
    
    def __init__(self):
        self.teams = ["india", "australia", "england", "south_africa", "new_zealand", "pakistan"]
        self.venues = ["mumbai", "melbourne", "lords", "cape_town", "auckland", "lahore"]
        self._mock_results = {}
        
    def fetch_upcoming_matches(self, days_ahead: int = 7) -> List[Dict]:
        matches = []
        for i in range(5): # Generate 5 mock matches
            team_a, team_b = random.sample(self.teams, 2)
            venue = random.choice(self.venues)
            match_date = datetime.now() + timedelta(days=random.randint(1, days_ahead))
            match_id = f"mock_{match_date.strftime('%Y%m%d')}_{team_a}_{team_b}"
            
            matches.append({
                "match_id": match_id,
                "date": match_date,
                "team_a": team_a,
                "team_b": team_b,
                "venue": venue,
                "match_type": "T20"
            })
            
            # Pre-decide the result for verification testing later
            self._mock_results[match_id] = random.choice([team_a, team_b])
            
        return matches

    def fetch_match_result(self, match_id: str) -> Optional[str]:
        # Return the pre-decided mock result
        return self._mock_results.get(match_id)


class CricAPIProvider(BaseLiveProvider):
    """Actual CricAPI integration (Implementation placeholder until API key is active)."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def fetch_upcoming_matches(self, days_ahead: int = 7) -> List[Dict]:
        # TODO: Implement requests.get('https://api.cricapi.com/v1/matches?apikey=...')
        return []
        
    def fetch_match_result(self, match_id: str) -> Optional[str]:
        # TODO: Implement endpoint
        return None

def get_live_provider() -> BaseLiveProvider:
    provider_name = os.environ.get("LIVE_PROVIDER", "mock").lower()
    
    if provider_name == "cricapi":
        return CricAPIProvider(api_key=os.environ.get("CRICAPI_KEY", ""))
    elif provider_name == "sportmonks":
        # Placeholder for another provider
        pass
        
    # Default to mock
    return MockProvider()
