"""
Weather Connector — dual-source strategy.

Primary:  OpenWeatherMap (requires API key — now configured)
Fallback: Open-Meteo   (free, no key, used for historical data & if OWM fails)

Set key in .env: OPENWEATHER_KEY=your_key_here
"""
import logging
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

OWM_CURRENT_URL   = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL  = "https://api.openweathermap.org/data/2.5/forecast"
OPEN_METEO_HIST   = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FCAST  = "https://api.open-meteo.com/v1/forecast"
ELEVATION_URL     = "https://api.open-elevation.com/api/v1/lookup"

# Approximate coordinates for common cricket venues
VENUE_COORDINATES = {
    "wankhede_stadium":                    (18.9388,  72.8258),
    "eden_gardens":                        (22.5645,  88.3433),
    "m_chinnaswamy_stadium":               (12.9788,  77.5996),
    "rajiv_gandhi_international_stadium":  (17.4040,  78.5440),
    "arun_jaitley_stadium":                (28.6364,  77.2369),
    "ma_chidambaram_stadium":              (13.0634,  80.2787),
    "sardar_patel_stadium":                (22.9972,  72.5849),
    "punjab_cricket_association_stadium":  (30.7004,  76.7170),
    "mcg":                                 (-37.8200, 144.9834),
    "scg":                                 (-33.8910, 151.2249),
    "adelaide_oval":                       (-34.9158, 138.5961),
    "gabba":                               (-27.4858, 153.0381),
    "perth_stadium":                       (-31.9505, 115.8605),
    "lords":                               (51.5260,  -0.1728),
    "the_oval":                            (51.4837,  -0.1150),
    "headingley":                          (53.8172,  -1.5814),
    "edgbaston":                           (52.4558,  -1.9025),
    "old_trafford":                        (53.4568,  -2.2877),
    "newlands":                            (-33.9995,  18.4249),
    "wanderers_stadium":                   (-26.1479,  28.0441),
    "national_stadium":                    (24.8608,  67.0104),
    "gaddafi_stadium":                     (31.5107,  74.3302),
    "hagley_oval":                         (-43.5272, 172.6369),
    "eden_park":                           (-36.8754, 174.7444),
    "unknown":                             (20.0,     77.0),
}


def _slug(name: str) -> str:
    if not name:
        return "unknown"
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


class WeatherConnector:
    """
    Fetches weather features for a venue + date.
    Uses OpenWeatherMap for current/forecast, Open-Meteo for historical.
    """

    def __init__(self, owm_key: Optional[str] = None):
        self.owm_key = owm_key or os.environ.get("OPENWEATHER_KEY", "")

    def _get_coords(self, venue_id: str):
        key = _slug(venue_id)
        return VENUE_COORDINATES.get(key, VENUE_COORDINATES["unknown"])

    def _get_elevation(self, lat: float, lon: float) -> float:
        try:
            resp = requests.get(ELEVATION_URL, params={"locations": f"{lat},{lon}"}, timeout=5)
            if resp.ok:
                return float(resp.json()["results"][0].get("elevation", 0.0))
        except Exception:
            pass
        return 0.0

    def _default_features(self, lat: float, lon: float) -> Dict[str, float]:
        return {
            "env_temperature_c":    25.0,
            "env_humidity_pct":     60.0,
            "env_precipitation_mm": 0.0,
            "env_windspeed_kmh":    15.0,
            "env_cloud_cover_pct":  30.0,
            "env_altitude_m":       0.0,
            "env_venue_latitude":   lat,
            "env_venue_longitude":  lon,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=8))
    def fetch_weather(self, venue_id: str, match_date: datetime) -> Dict[str, float]:
        """
        Returns weather features dict for the given venue and date.
        Automatically picks the best available source.
        """
        lat, lon = self._get_coords(venue_id)
        features = self._default_features(lat, lon)
        today     = datetime.utcnow().date()
        match_day = match_date.date() if hasattr(match_date, 'date') else match_date

        try:
            if match_day >= today:
                # ── Future / current: use OpenWeatherMap ─────────────────
                if self.owm_key:
                    features.update(self._fetch_owm_forecast(lat, lon, match_day, today))
                else:
                    features.update(self._fetch_openmeteo_forecast(lat, lon, match_day))
            else:
                # ── Historical: Open-Meteo is best (OWM free tier = current only) ──
                features.update(self._fetch_openmeteo_historical(lat, lon, match_day))

            features["env_altitude_m"] = self._get_elevation(lat, lon)

        except Exception as e:
            logging.warning(f"Weather fetch failed for {venue_id}/{match_day}: {e}. Using defaults.")

        return features

    def _fetch_owm_forecast(self, lat, lon, match_day, today) -> Dict:
        """OpenWeatherMap 5-day forecast (free tier)."""
        delta = (match_day - today).days
        resp = requests.get(
            OWM_FORECAST_URL,
            params={"lat": lat, "lon": lon, "appid": self.owm_key,
                    "units": "metric", "cnt": min(40, max(8, delta * 8))},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        forecasts = data.get("list", [])

        if not forecasts:
            return {}

        # Take the closest forecast to the target date at noon
        target_ts = datetime.combine(match_day, datetime.min.time()).replace(hour=12)
        best = min(
            forecasts,
            key=lambda x: abs(datetime.utcfromtimestamp(x["dt"]) - target_ts)
        )
        main  = best.get("main", {})
        wind  = best.get("wind", {})
        cloud = best.get("clouds", {})
        rain  = best.get("rain", {})

        return {
            "env_temperature_c":    main.get("temp", 25.0),
            "env_humidity_pct":     main.get("humidity", 60.0),
            "env_precipitation_mm": rain.get("3h", 0.0),
            "env_windspeed_kmh":    wind.get("speed", 15.0) * 3.6,  # m/s → km/h
            "env_cloud_cover_pct":  cloud.get("all", 30.0),
        }

    def _fetch_openmeteo_historical(self, lat, lon, match_day) -> Dict:
        """Open-Meteo historical archive — always free, no key needed."""
        date_str = match_day.strftime("%Y-%m-%d")
        next_str = (match_day + timedelta(days=1)).strftime("%Y-%m-%d")
        resp = requests.get(
            OPEN_METEO_HIST,
            params={
                "latitude": lat, "longitude": lon,
                "start_date": date_str, "end_date": next_str,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                         "windspeed_10m_max,cloudcover_mean",
                "timezone": "UTC"
            },
            timeout=10
        )
        resp.raise_for_status()
        daily = resp.json().get("daily", {})
        if not daily or not daily.get("temperature_2m_max"):
            return {}

        t_max = daily["temperature_2m_max"][0] or 30.0
        t_min = daily["temperature_2m_min"][0] or 20.0
        return {
            "env_temperature_c":    (t_max + t_min) / 2,
            "env_precipitation_mm": (daily.get("precipitation_sum", [0.0])[0] or 0.0),
            "env_windspeed_kmh":    (daily.get("windspeed_10m_max",  [15.0])[0] or 15.0),
            "env_cloud_cover_pct":  (daily.get("cloudcover_mean",    [30.0])[0] or 30.0),
            "env_humidity_pct":     60.0,  # Not available in free Open-Meteo daily
        }

    def _fetch_openmeteo_forecast(self, lat, lon, match_day) -> Dict:
        """Open-Meteo forecast — free fallback when no OWM key."""
        date_str = match_day.strftime("%Y-%m-%d")
        resp = requests.get(
            OPEN_METEO_FCAST,
            params={
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                "forecast_days": 16, "timezone": "UTC"
            },
            timeout=10
        )
        resp.raise_for_status()
        daily = resp.json().get("daily", {})
        dates = daily.get("time", [])

        if date_str in dates:
            idx = dates.index(date_str)
            t_max = daily["temperature_2m_max"][idx] or 30.0
            t_min = daily["temperature_2m_min"][idx] or 20.0
            return {
                "env_temperature_c":    (t_max + t_min) / 2,
                "env_precipitation_mm": daily.get("precipitation_sum", [0.0])[idx] or 0.0,
                "env_windspeed_kmh":    daily.get("windspeed_10m_max",  [15.0])[idx] or 15.0,
                "env_humidity_pct":     60.0,
                "env_cloud_cover_pct":  30.0,
            }
        return {}
