import logging
from typing import Dict, Any
from datetime import datetime
from core.models.base_event import BaseEvent
from core.generators.base_generator import BaseFeatureGenerator
from core.generators.cache import FeatureCache

try:
    import swisseph as swe
    HAS_SWISSEPH = True
except ImportError:
    logging.warning("swisseph module not found. AstronomyGenerator will return empty features.")
    HAS_SWISSEPH = False

class AstronomyGenerator(BaseFeatureGenerator):
    """
    Generates universal astronomical features using the Swiss Ephemeris.
    These features represent raw celestial positions and states at the exact time
    and location of the event. The ML engine will determine if they hold predictive value.
    """
    
    def __init__(self):
        # Configure Swiss Ephemeris if necessary (e.g., setting ephe path)
        pass

    @property
    def generator_name(self) -> str:
        return "AstronomyGenerator"

    def _datetime_to_julian(self, dt: datetime) -> float:
        """Converts datetime to Julian day for swisseph."""
        if not HAS_SWISSEPH:
            return 0.0
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)

    def generate(self, event: BaseEvent) -> Dict[str, float]:
        """
        Calculates positions for major planets, lunar nodes, Tithi, and Nakshatra.
        Uses FeatureCache to avoid recalculating if the date/location matches.
        """
        if not HAS_SWISSEPH:
            return {}
            
        cache_key = FeatureCache.generate_key(self.generator_name, event.date, event.location)
        
        def _compute():
            features = {}
            jd = self._datetime_to_julian(event.date)
            
            flag = swe.FLG_SWIEPH
            planets = {
                'sun': swe.SUN,
                'moon': swe.MOON,
                'mercury': swe.MERCURY,
                'venus': swe.VENUS,
                'mars': swe.MARS,
                'jupiter': swe.JUPITER,
                'saturn': swe.SATURN,
                'rahu': swe.MEAN_NODE # North Node
            }
            positions = {}
            
            # 1. Planetary Positions and Retrograde
            for name, planet_id in planets.items():
                res, _ = swe.calc_ut(jd, planet_id, flag)
                lon, speed = res[0], res[3]
                features[f"astro_{name}_lon"] = lon
                features[f"astro_{name}_retrograde"] = 1.0 if speed < 0 else 0.0
                positions[name] = lon
                
            # 2. Tithi
            angle = positions['moon'] - positions['sun']
            if angle < 0: angle += 360.0
            features["astro_tithi"] = (angle / 12.0) + 1
            
            # 3. Nakshatra
            swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
            res_sid, _ = swe.calc_ut(jd, swe.MOON, flag | swe.FLG_SIDEREAL)
            features["astro_nakshatra"] = (res_sid[0] / (360.0 / 27.0)) + 1
            swe.set_sid_mode(0, 0, 0)
            
            # 4. Moon Phase
            res_pheno, _ = swe.pheno_ut(jd, swe.MOON, flag)
            features["astro_moon_phase_fraction"] = res_pheno[1]
            
            return features

        return FeatureCache.get_or_compute(cache_key, _compute)

