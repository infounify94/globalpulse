import unittest
import sys
import os

# Add project root to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models.base_event import BaseEvent
from plugins.cricket.cricket_event import CricketEvent
from core.generators.astronomy_generator import AstronomyGenerator
from plugins.cricket.cricket_stats_generator import CricketStatsGenerator
from datetime import datetime

class TestArchitecture(unittest.TestCase):
    
    def test_plugin_inheritance(self):
        """Verify that CricketEvent correctly inherits from BaseEvent."""
        event = CricketEvent(
            id="test_match_1",
            date=datetime(2023, 10, 15, 14, 0, 0),
            location="Ahmedabad",
            participants=["India", "Pakistan"],
            match_type="ODI",
            venue_name="Narendra Modi Stadium",
            team_a="India",
            team_b="Pakistan"
        )
        self.assertIsInstance(event, BaseEvent)
        self.assertEqual(event.match_type, "ODI")
        
    def test_generators(self):
        """Verify generators implement the interface."""
        astro = AstronomyGenerator()
        stats = CricketStatsGenerator()
        
        self.assertEqual(astro.generator_name, "AstronomyGenerator")
        self.assertEqual(stats.generator_name, "CricketStatsGenerator")

if __name__ == '__main__':
    unittest.main()
