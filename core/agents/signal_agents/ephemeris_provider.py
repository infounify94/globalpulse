import abc
from datetime import datetime
from typing import Dict, Any

class EphemerisProvider(abc.ABC):
    """
    Abstract interface for planetary calculations.
    Ensures that we can swap between Skyfield (NASA JPL) and Swiss Ephemeris
    if needed in the future, while maintaining consistent outputs for the ML pipeline.
    """
    
    @abc.abstractmethod
    def get_planetary_positions(self, dt: datetime, geocentric: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Calculates the position of planets for a specific historical date.
        Returns a dictionary mapping planet names to their coordinates.
        Example output:
        {
            'jupiter': {'longitude': 120.5, 'latitude': -1.2, 'retrograde': False},
            'saturn': {'longitude': 45.2, 'latitude': 0.8, 'retrograde': True},
            ...
        }
        """
        pass
