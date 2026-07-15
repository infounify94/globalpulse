"""
Phase 9 Signal Agent: Historical Weather Features.
Fetches match-day weather from the Open-Meteo Historical Archive API.
Returns temperature, precipitation, wind speed, and relative humidity
for the match venue on the match date. Fails silently on any error.
"""

import requests
from typing import Dict, Any

# ---------------------------------------------------------------------------
# Venue → (latitude, longitude) lookup for major cricket venues
# ---------------------------------------------------------------------------
VENUE_COORDINATES: Dict[str, tuple] = {
    # India
    "mumbai":       (19.0760, 72.8777),
    "chennai":      (13.0827, 80.2707),
    "delhi":        (28.6139, 77.2090),
    "kolkata":      (22.5726, 88.3639),
    "hyderabad":    (17.3850, 78.4867),
    "bengaluru":    (12.9716, 77.5946),
    "bangalore":    (12.9716, 77.5946),
    "pune":         (18.5204, 73.8567),
    "ahmedabad":    (23.0225, 72.5714),
    "rajkot":       (22.3039, 70.8022),
    "nagpur":       (21.1458, 79.0882),
    "indore":       (22.7196, 75.8577),
    "visakhapatnam":(17.6868, 83.2185),
    "mohali":       (30.7046, 76.7179),
    "chandigarh":   (30.7333, 76.7794),
    "cuttack":      (20.4625, 85.8828),
    "dharamsala":   (32.2190, 76.3234),
    "ranchi":       (23.3441, 85.3096),
    "raipur":       (21.2514, 81.6296),
    "trivandrum":   (8.5241, 76.9366),
    "thiruvananthapuram": (8.5241, 76.9366),

    # International
    "london":       (51.5074, -0.1278),
    "birmingham":   (52.4862, -1.8904),
    "manchester":   (53.4808, -2.2426),
    "leeds":        (53.8008, -1.5491),
    "cardiff":      (51.4816, -3.1791),
    "bristol":      (51.4545, -2.5879),
    "chester-le-street": (54.8570, -1.5760),
    "nottingham":   (52.9548, -1.1581),
    "southampton":  (50.9097, -1.4044),
    "melbourne":    (-37.8136, 144.9631),
    "sydney":       (-33.8688, 151.2093),
    "brisbane":     (-27.4698, 153.0251),
    "perth":        (-31.9505, 115.8605),
    "adelaide":     (-34.9285, 138.6007),
    "hobart":       (-42.8821, 147.3272),
    "johannesburg": (-26.2041, 28.0473),
    "cape town":    (-33.9249, 18.4241),
    "durban":       (-29.8587, 31.0218),
    "centurion":    (-25.8600, 28.1889),
    "port elizabeth":(-33.9608, 25.6022),
    "dubai":        (25.2048, 55.2708),
    "abu dhabi":    (24.4539, 54.3773),
    "sharjah":      (25.3463, 55.4209),
    "karachi":      (24.8607, 67.0011),
    "lahore":       (31.5204, 74.3587),
    "islamabad":    (33.6844, 73.0479),
    "rawalpindi":   (33.5651, 73.0169),
    "multan":       (30.1798, 71.4214),
    "colombo":      (6.9271, 79.8612),
    "kandy":        (7.2906, 80.6337),
    "galle":        (6.0535, 80.2210),
    "dhaka":        (23.8103, 90.4125),
    "chittagong":   (22.3569, 91.7832),
    "mirpur":       (23.8041, 90.3517),
    "auckland":     (-36.8485, 174.7633),
    "wellington":   (-41.2865, 174.7762),
    "christchurch": (-43.5321, 172.6362),
    "hamilton":     (-37.7870, 175.2793),
    "napier":       (-39.4928, 176.9120),
    "kingston":     (17.9970, -76.7936),
    "bridgetown":   (13.0969, -59.6145),
    "port of spain":(10.6918, -61.2225),
    "st. john's":   (17.1274, -61.8468),
    "harare":       (-17.8252, 31.0335),
    "nairobi":      (-1.2921, 36.8219),
    "edinburgh":    (55.9533, -3.1883),
}


def _resolve_venue(venue_str: str):
    """
    Try to match a venue string to coordinates via fuzzy city name lookup.
    Returns (lat, lon) tuple or None if not found.
    """
    if not venue_str:
        return None
    venue_lower = venue_str.lower().strip()
    # Direct city name match
    for city, coords in VENUE_COORDINATES.items():
        if city in venue_lower:
            return coords
    return None


class WeatherAgent:
    """
    Fetches historical match-day weather for a given venue and date
    from the Open-Meteo Historical Archive API.

    Features returned:
        temperature_2m_max      : Max temperature (deg C)
        precipitation_sum       : Total precipitation (mm)
        windspeed_10m_max       : Max wind speed (km/h)
        relative_humidity_mean  : Estimated mean relative humidity (%)

    Returns an empty dict silently on any failure (unknown venue, API error, etc.).
    """

    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    TIMEOUT = 5  # seconds

    def compute_features(self, match_date_str: str, venue: str) -> Dict[str, float]:
        """
        Parameters
        ----------
        match_date_str : str
            Date string in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' format.
        venue : str
            Free-text venue / city name (e.g. 'Wankhede Stadium, Mumbai').

        Returns
        -------
        Dict[str, float]
            Weather feature dict. Empty on failure.
        """
        try:
            date_str = str(match_date_str)[:10]  # Take 'YYYY-MM-DD' portion

            coords = _resolve_venue(venue)
            if coords is None:
                return {}

            lat, lon = coords

            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": date_str,
                "end_date": date_str,
                "daily": ",".join([
                    "temperature_2m_max",
                    "precipitation_sum",
                    "windspeed_10m_max",
                    "relative_humidity_2m_max",
                    "relative_humidity_2m_min",
                ]),
                "timezone": "auto",
            }

            response = requests.get(self.BASE_URL, params=params, timeout=self.TIMEOUT)
            if response.status_code != 200:
                return {}

            data = response.json()
            daily = data.get("daily", {})

            def _first(key):
                vals = daily.get(key, [None])
                return vals[0] if vals else None

            temp_max = _first("temperature_2m_max")
            precip   = _first("precipitation_sum")
            wind_max = _first("windspeed_10m_max")
            hum_max  = _first("relative_humidity_2m_max")
            hum_min  = _first("relative_humidity_2m_min")

            # Derived mean humidity
            if hum_max is not None and hum_min is not None:
                hum_mean = (hum_max + hum_min) / 2.0
            elif hum_max is not None:
                hum_mean = hum_max
            elif hum_min is not None:
                hum_mean = hum_min
            else:
                hum_mean = None

            features: Dict[str, float] = {}
            if temp_max is not None:
                features["temperature_2m_max"] = float(temp_max)
            if precip is not None:
                features["precipitation_sum"] = float(precip)
            if wind_max is not None:
                features["windspeed_10m_max"] = float(wind_max)
            if hum_mean is not None:
                features["relative_humidity_mean"] = float(hum_mean)

            return features

        except Exception:
            # Fail silently - weather data is an optional signal
            return {}


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    agent = WeatherAgent()
    result = agent.compute_features("2023-04-15", "Wankhede Stadium, Mumbai")
    print("Weather features for Mumbai 2023-04-15:", result)
    result2 = agent.compute_features("2019-07-14", "Lord's Cricket Ground, London")
    print("Weather features for London 2019-07-14:", result2)
