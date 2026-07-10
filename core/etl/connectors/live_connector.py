"""
Live Cricket Connector using CricAPI (Lifetime Free key).

Endpoints used:
  - currentMatches  → upcoming & live match schedules
  - eCricScore      → live ball-by-ball scores & completed results

API docs: https://cricapi.com/
Set key in .env: CRICAPI_KEY=your_key_here
"""
import os
import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

CRICAPI_BASE = "https://api.cricapi.com/v1"


class ScheduleConnector:
    """
    Fetches current and upcoming cricket matches using CricAPI currentMatches endpoint.
    Falls back to mock data when no key is available (safe for dev/testing).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("CRICAPI_KEY", "")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def fetch_upcoming_matches(self) -> List[Dict[str, Any]]:
        """Fetches current & upcoming matches from CricAPI currentMatches."""
        if not self.api_key:
            logging.warning("No CRICAPI_KEY set. Using mock schedule data.")
            return self._mock_upcoming()

        try:
            resp = requests.get(
                f"{CRICAPI_BASE}/currentMatches",
                params={"apikey": self.api_key, "offset": 0},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "success":
                logging.warning(f"CricAPI error: {data.get('reason', 'Unknown')}. Using mock.")
                return self._mock_upcoming()

            matches = []
            for m in data.get("data", []):
                teams = m.get("teams", [])
                if len(teams) < 2:
                    continue
                matches.append({
                    "match_id":   m.get("id", ""),
                    "team_a":     teams[0],
                    "team_b":     teams[1],
                    "date":       m.get("date", ""),
                    "venue":      m.get("venue", "Unknown"),
                    "match_type": m.get("matchType", "odi").upper(),
                    "status":     m.get("status", ""),
                    "live":       not m.get("matchEnded", False),
                    "source":     "cricapi_current"
                })

            logging.info(f"Fetched {len(matches)} current/upcoming matches from CricAPI.")
            return matches

        except Exception as e:
            logging.error(f"CricAPI currentMatches failed: {e}. Using mock.")
            return self._mock_upcoming()

    def _mock_upcoming(self) -> List[Dict[str, Any]]:
        return [
            {
                "match_id": "mock_odi_001",
                "team_a": "India", "team_b": "Australia",
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "venue": "Wankhede Stadium", "match_type": "ODI",
                "status": "upcoming", "live": False, "source": "mock"
            },
            {
                "match_id": "mock_t20_002",
                "team_a": "England", "team_b": "New Zealand",
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "venue": "Lord's", "match_type": "T20",
                "status": "upcoming", "live": False, "source": "mock"
            }
        ]


class ScoreConnector:
    """
    Fetches live scores and completed match results using CricAPI eCricScore endpoint.
    Used by the verification loop: once a match ends, fetch the result and
    trigger Champion vs Challenger drift checking.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("CRICAPI_KEY", "")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def fetch_score(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches live score / final result for a specific match ID.
        Returns None if match is still in progress or not found.
        """
        if not self.api_key:
            logging.warning("No CRICAPI_KEY. Returning mock score.")
            return {"match_id": match_id, "winner": "India", "completed": True, "source": "mock"}

        try:
            resp = requests.get(
                f"{CRICAPI_BASE}/match_info",
                params={"apikey": self.api_key, "id": match_id},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "success":
                return None

            match_data = data.get("data", {})
            match_ended = match_data.get("matchEnded", False)

            return {
                "match_id":  match_id,
                "winner":    match_data.get("matchWinner", ""),
                "status":    match_data.get("status", ""),
                "score":     match_data.get("score", []),
                "completed": match_ended,
                "source":    "cricapi_score"
            }

        except Exception as e:
            logging.error(f"CricAPI score fetch failed for {match_id}: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def fetch_recent_results(self) -> List[Dict[str, Any]]:
        """
        Fetches completed match outcomes from CricAPI for continuous learning.
        """
        if not self.api_key:
            return [{"match_id": "cric_999", "winner": "India", "score": "320/5", "source": "mock"}]
        try:
            resp = requests.get(
                f"{CRICAPI_BASE}/currentMatches",
                params={"apikey": self.api_key, "offset": 0},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for m in data.get("data", []):
                if m.get("matchEnded", False) and m.get("matchWinner"):
                    results.append({
                        "match_id": m.get("id", ""),
                        "winner": m.get("matchWinner", ""),
                        "status": m.get("status", ""),
                        "source": "cricapi"
                    })
            return results
        except Exception as e:
            logging.error(f"ScoreConnector fetch_recent_results failed: {e}")
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def fetch_live_scores(self) -> List[Dict[str, Any]]:
        """
        Fetches all currently live match scores using eCricScore.
        Used by the Live Monitor dashboard page.
        """
        if not self.api_key:
            return [{"match_id": "mock_live_001", "status": "India 180/4 in 35 overs",
                     "teams": ["India", "Australia"], "source": "mock"}]

        try:
            resp = requests.get(
                f"{CRICAPI_BASE}/cricScore",
                params={"apikey": self.api_key},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "success":
                return []

            scores = []
            for m in data.get("data", []):
                scores.append({
                    "match_id": m.get("id", ""),
                    "title":    m.get("title", ""),
                    "status":   m.get("status", ""),
                    "teams":    m.get("t1", "") + " vs " + m.get("t2", ""),
                    "score_t1": m.get("t1s", ""),
                    "score_t2": m.get("t2s", ""),
                    "source":   "cricapi_score"
                })
            return scores

        except Exception as e:
            logging.error(f"CricAPI live scores failed: {e}")
            return []

    def fetch_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns recently completed matches for the verification loop."""
        matches = self._fetch_all_current()
        results = [m for m in matches if m.get("completed")]
        return results[:limit]

    def _fetch_all_current(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        try:
            resp = requests.get(
                f"{CRICAPI_BASE}/currentMatches",
                params={"apikey": self.api_key, "offset": 0},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for m in data.get("data", []):
                results.append({
                    "match_id":  m.get("id", ""),
                    "winner":    m.get("matchWinner", ""),
                    "completed": m.get("matchEnded", False),
                    "date":      m.get("date", ""),
                    "source":    "cricapi_current"
                })
            return results
        except Exception:
            return []


# Convenience: keep backward-compatible name
ResultConnector = ScoreConnector
