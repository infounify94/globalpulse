import os
import sys
from datetime import datetime
from typing import Dict, Any

# Ensure python can find the core module
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.agents.signal_agents.ephemeris_provider import EphemerisProvider

class SkyfieldEphemeris(EphemerisProvider):
    """
    Skyfield implementation of EphemerisProvider.
    Downloads and caches NASA JPL DE421 ephemeris locally (offline reproducibility).
    Calculates geocentric ecliptic longitude/latitude.
    """
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.path.join(BASE_DIR, "data", "datasets", "ephemeris")
        
        os.makedirs(data_dir, exist_ok=True)
        
        try:
            from skyfield.api import Loader
            load = Loader(data_dir)
            self.load = load
            # Download or load the de421.bsp file (covers 1900 to 2050)
            self.planets = load('de421.bsp')
            self.ts = load.timescale()
        except ImportError:
            print("Warning: Skyfield is not installed. Run 'pip install skyfield'.")
            self.planets = None
            self.ts = None

        self.planet_map = {
            'sun': self.planets['sun'],
            'moon': self.planets['moon'],
            'mercury': self.planets['mercury'],
            'venus': self.planets['venus'],
            'mars': self.planets['mars'],
            'jupiter': self.planets['jupiter barycenter'],
            'saturn': self.planets['saturn barycenter'],
            # Optional in Vedic, but adding for completeness
            'uranus': self.planets['uranus barycenter'],
            'neptune': self.planets['neptune barycenter'],
        }
        self.earth = self.planets['earth']

    def get_planetary_positions(self, dt: datetime, geocentric: bool = True) -> Dict[str, Dict[str, Any]]:
        if self.planets is None:
            raise RuntimeError("Skyfield not installed or ephemeris failed to load.")
            
        t = self.ts.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        
        # Calculate positions
        results = {}
        for name, body in self.planet_map.items():
            if geocentric:
                astrometric = self.earth.at(t).observe(body)
            else:
                astrometric = body.at(t) # heliocentric if observing from barycenter (approx)
                
            # Apparent position in ecliptic coordinates (longitude, latitude)
            lat, lon, distance = astrometric.ecliptic_latlon('date')
            
            # Simple retrograde check: is longitude decreasing?
            # We check 1 hour ahead
            t_next = self.ts.utc(dt.year, dt.month, dt.day, dt.hour + 1, dt.minute, dt.second)
            if geocentric:
                astrometric_next = self.earth.at(t_next).observe(body)
                _, lon_next, _ = astrometric_next.ecliptic_latlon('date')
                
                # Handle 360 wrap around
                diff = lon_next.degrees - lon.degrees
                if diff < -180: diff += 360
                elif diff > 180: diff -= 360
                
                retrograde = diff < 0
            else:
                retrograde = False # Heliocentric rarely retrograde for outer planets in simple terms
                
            results[name] = {
                'longitude': lon.degrees,
                'latitude': lat.degrees,
                'distance_au': distance.au,
                'retrograde': retrograde
            }
            
        return results
