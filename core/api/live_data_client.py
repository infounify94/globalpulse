import os
import requests

CRICAPI_KEY = "bd50097b-082d-4d9d-88aa-b0e47a1bb9cc"
BASE_URL = "https://api.cricapi.com/v1"

class LiveDataClient:
    def __init__(self, api_key=CRICAPI_KEY):
        self.api_key = api_key

    def get_upcoming_matches(self):
        """Fetch upcoming matches from CricAPI."""
        url = f"{BASE_URL}/matches?apikey={self.api_key}&offset=0"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
        except Exception as e:
            print(f"API Error fetching matches: {e}")
            return []

    def get_match_info(self, match_id):
        """Fetch live toss, playing XI, and venue conditions for a match."""
        url = f"{BASE_URL}/match_info?apikey={self.api_key}&id={match_id}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {})
            return {}
        except Exception as e:
            print(f"API Error fetching match info: {e}")
            return {}

    def get_fantasy_squad(self, match_id):
        """Fetch playing XI directly from fantasy squad endpoint."""
        url = f"{BASE_URL}/match_squad?apikey={self.api_key}&id={match_id}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
        except Exception as e:
            print(f"API Error fetching match squad: {e}")
            return []

    def scraper_fallback_playing_xi(self, match_id):
        """
        Fallback web-scraper if the API goes down or rate limits.
        (Stub logic for future ESPNCricinfo integration)
        """
        print("API Failed. Initializing Scraper Fallback...")
        return {"status": "Waiting for Playing XI"}
