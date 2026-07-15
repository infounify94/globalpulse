import os
import sys
from typing import Dict, Any
from datetime import datetime

# Ensure python can find the core module
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.agents.research_pipeline.feature_generator import FeatureGenerator
from core.agents.signal_agents.skyfield_ephemeris import SkyfieldEphemeris

class PlanetaryAgent(FeatureGenerator):
    """
    Extracts Vedic/Babylonian ephemeris features (Planetary positions).
    Uses NASA JPL DE421 ephemeris locally to prevent look-ahead bias.
    """
    def __init__(self, ephemeris_provider=None):
        self.ephemeris = ephemeris_provider or SkyfieldEphemeris()
        
    def _longitude_to_zodiac_idx(self, lon: float) -> int:
        """Convert 0-360 longitude to 12 zodiac signs (0-11). Returning int for ML model."""
        return int(lon // 30) % 12

    def _longitude_to_nakshatra_idx(self, lon: float) -> int:
        """Convert 0-360 longitude to 27 Nakshatras (0-26). Each is 13 degrees 20 minutes (40/3 degrees)."""
        return int(lon / (40.0 / 3.0)) % 27
        
    def _get_aspect(self, lon1: float, lon2: float) -> float:
        """Returns the shortest angular distance between two planets (0 to 180 degrees)."""
        diff = abs(lon1 - lon2)
        if diff > 180:
            diff = 360 - diff
        return diff

    def compute_features(self, match_metadata: Dict[str, Any], match_date_str: str) -> Dict[str, float]:
        """
        Compute Planetary features for a match strictly using knowledge exactly at the match date.
        """
        try:
            # Handle pandas Timestamp strings (e.g., '2017-02-17 00:00:00')
            match_date_str = match_date_str.replace(" ", "T")
            
            # We assume ISO8601 or YYYY-MM-DD
            if 'T' in match_date_str:
                dt = datetime.strptime(match_date_str[:19], "%Y-%m-%dT%H:%M:%S")
            else:
                dt = datetime.strptime(match_date_str[:10], "%Y-%m-%d")
        except Exception as e:
            print(f"Date parse error for {match_date_str}: {e}")
            return {}
            
        try:
            positions = self.ephemeris.get_planetary_positions(dt, geocentric=True)
            
            # Extract longitudes
            j_lon = positions['jupiter']['longitude']
            s_lon = positions['saturn']['longitude']
            m_lon = positions['mars']['longitude']
            sun_lon = positions['sun']['longitude']
            moon_lon = positions['moon']['longitude']

            features = {
                # Basic Zodiacs
                'jupiter_sign': float(self._longitude_to_zodiac_idx(j_lon)),
                'saturn_sign': float(self._longitude_to_zodiac_idx(s_lon)),
                'mars_sign': float(self._longitude_to_zodiac_idx(m_lon)),
                'sun_sign': float(self._longitude_to_zodiac_idx(sun_lon)),
                'moon_sign': float(self._longitude_to_zodiac_idx(moon_lon)),
                
                # Advanced: Nakshatras (Vedic Lunar Mansions)
                'moon_nakshatra': float(self._longitude_to_nakshatra_idx(moon_lon)),
                'sun_nakshatra': float(self._longitude_to_nakshatra_idx(sun_lon)),
                'jupiter_nakshatra': float(self._longitude_to_nakshatra_idx(j_lon)),
                
                # Advanced: Exact Planetary Aspects (Angular Distances)
                'sun_moon_angle': self._get_aspect(sun_lon, moon_lon),
                'sun_jupiter_angle': self._get_aspect(sun_lon, j_lon),
                'mars_saturn_angle': self._get_aspect(m_lon, s_lon),
                
                # Retrograde status
                'jupiter_retrograde': float(positions['jupiter']['retrograde']),
                'saturn_retrograde': float(positions['saturn']['retrograde']),
                'mars_retrograde': float(positions['mars']['retrograde'])
            }
            return features
        except Exception as e:
            print(f"Error calculating ephemeris for {dt}: {e}")
            return {}

if __name__ == "__main__":
    # Structural Test
    agent = PlanetaryAgent()
    
    # Test date: 2011 World Cup Final (April 2, 2011)
    match_meta = {"team1": "India", "team2": "Sri Lanka"}
    date_str = "2011-04-02T14:30:00Z"
    
    print(f"Testing PlanetaryAgent for 2011 WC Final ({date_str}):")
    res = agent.compute_features(match_meta, date_str)
    for k, v in res.items():
        print(f"{k}: {v}")
