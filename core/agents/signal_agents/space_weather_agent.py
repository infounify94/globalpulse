"""
Phase 9 Signal Agent: Space Weather Features.
Fetches historical geomagnetic and solar activity data for a given date.

Features returned:
    kp_index_max    : Daily maximum Kp geomagnetic index (0-9)
    solar_flux_f107 : Solar radio flux at 10.7 cm (sfu)

Data sources:
    Kp Index  - GFZ Potsdam: https://kp.gfz-potsdam.de/app/json/
    F10.7     - NOAA SWPC:   https://services.swpc.noaa.gov/json/f107_cm_flux.json

Results are cached in-memory per date to avoid redundant API calls.
Fails silently on any network or parse error.
"""

import requests
from typing import Dict, Optional
from datetime import datetime, timedelta

KP_API_URL = (
    "https://kp.gfz-potsdam.de/app/json/"
    "?start={date}T00:00:00Z&end={date}T23:59:00Z&index=Kp"
)
F107_API_URL = "https://services.swpc.noaa.gov/json/f107_cm_flux.json"

TIMEOUT = 5  # seconds


class SpaceWeatherAgent:
    """
    Provides daily space-weather features: geomagnetic Kp index and solar F10.7 flux.

    Instance-level caches prevent repeated HTTP calls for the same date within
    a single benchmark run.
    """

    def __init__(self):
        self._kp_cache: Dict[str, float] = {}       # date_str -> kp_max
        self._f107_cache: Dict[str, float] = {}     # date_str -> f107
        self._f107_loaded: bool = False              # whether we've attempted the bulk fetch

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_features(self, match_date_str: str) -> Dict[str, float]:
        """
        Parameters
        ----------
        match_date_str : str
            Date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' format.

        Returns
        -------
        Dict[str, float]
            {'kp_index_max': float, 'solar_flux_f107': float}
            Either or both keys may be absent if the API call failed.
        """
        date_str = str(match_date_str)[:10]
        features: Dict[str, float] = {}

        kp_val = self._get_kp(date_str)
        if kp_val is not None:
            features["kp_index_max"] = float(kp_val)

        f107_val = self._get_f107(date_str)
        if f107_val is not None:
            features["solar_flux_f107"] = float(f107_val)

        return features

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_kp(self, date_str: str) -> Optional[float]:
        """Fetch or return cached daily maximum Kp index for date_str."""
        if date_str in self._kp_cache:
            return self._kp_cache[date_str]

        try:
            url = KP_API_URL.format(date=date_str)
            resp = requests.get(url, timeout=TIMEOUT)
            if resp.status_code != 200:
                return None

            data = resp.json()
            # The GFZ API returns a list of dicts with key 'Kp'
            # or an array under 'kp' depending on version.
            kp_values = []

            if isinstance(data, list):
                # Each element may be a dict with 'Kp' key
                for entry in data:
                    if isinstance(entry, dict):
                        for k in ("Kp", "kp", "KP"):
                            if k in entry and entry[k] is not None:
                                try:
                                    kp_values.append(float(entry[k]))
                                except (TypeError, ValueError):
                                    pass
                                break
            elif isinstance(data, dict):
                # Some versions nest under 'kp' key with array of values
                for k in ("Kp", "kp", "KP"):
                    if k in data:
                        raw = data[k]
                        if isinstance(raw, list):
                            for v in raw:
                                try:
                                    kp_values.append(float(v))
                                except (TypeError, ValueError):
                                    pass
                        break

            if kp_values:
                max_kp = max(kp_values)
                self._kp_cache[date_str] = max_kp
                return max_kp

            return None

        except Exception:
            return None

    def _load_f107_bulk(self):
        """
        Fetch the last-30-days F10.7 bulk feed from NOAA SWPC and populate cache.
        Called lazily the first time F10.7 is requested.
        """
        if self._f107_loaded:
            return
        self._f107_loaded = True

        try:
            resp = requests.get(F107_API_URL, timeout=TIMEOUT)
            if resp.status_code != 200:
                return

            data = resp.json()
            # Each entry is typically: {"time_tag": "2024-01-15T00:00:00", "flux": 152.3, ...}
            for entry in data:
                if not isinstance(entry, dict):
                    continue

                # Date key variants
                date_val = None
                for key in ("time_tag", "date", "Date", "TimeTag"):
                    if key in entry and entry[key]:
                        date_val = str(entry[key])[:10]
                        break

                # Flux key variants
                flux_val = None
                for key in ("flux", "Flux", "f107", "observed_flux", "adjusted_flux"):
                    if key in entry and entry[key] is not None:
                        try:
                            flux_val = float(entry[key])
                        except (TypeError, ValueError):
                            pass
                        if flux_val is not None:
                            break

                if date_val and flux_val is not None:
                    # Keep the last value if multiple entries share the same date
                    self._f107_cache[date_val] = flux_val

        except Exception:
            pass

    def _get_f107(self, date_str: str) -> Optional[float]:
        """Return F10.7 solar flux for date_str from cache (populated lazily)."""
        self._load_f107_bulk()

        if date_str in self._f107_cache:
            return self._f107_cache[date_str]

        # Try neighbours (±1 day) for robustness
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            for delta in (-1, 1, -2, 2):
                neighbour = (dt + timedelta(days=delta)).strftime("%Y-%m-%d")
                if neighbour in self._f107_cache:
                    return self._f107_cache[neighbour]
        except Exception:
            pass

        return None


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    agent = SpaceWeatherAgent()

    test_dates = ["2023-04-15", "2019-07-14", "2011-04-02"]
    for d in test_dates:
        feats = agent.compute_features(d)
        print(f"Space weather for {d}: {feats}")
