import unittest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.memory.schema import Base, DBEvent, DBCricketMatchMetadata, DBTeam, DBVenue
from plugins.cricket.cricket_event import CricketEvent
from plugins.cricket.cricket_stats_generator import CricketStatsGenerator

class TestFeatureLeakage(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database for testing
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        
        # Populate mock data
        with Session(self.engine) as session:
            session.add(DBTeam(id="team_ind", name="India", domain="cricket"))
            session.add(DBTeam(id="team_aus", name="Australia", domain="cricket"))
            session.add(DBVenue(id="v1", name="Venue 1"))
            
            # Match 1 (Past)
            m1 = DBEvent(id="match_1", event_type="cricket", date=datetime(2019, 5, 10), venue_id="v1", outcome="team_ind")
            m1_meta = DBCricketMatchMetadata(event_id="match_1", match_type="ODI", team_a_id="team_ind", team_b_id="team_aus")
            
            # Match 2 (Future - SHOULD NEVER LEAK into Match 1's features)
            m2 = DBEvent(id="match_2", event_type="cricket", date=datetime(2019, 5, 15), venue_id="v1", outcome="team_aus")
            m2_meta = DBCricketMatchMetadata(event_id="match_2", match_type="ODI", team_a_id="team_ind", team_b_id="team_aus")
            
            session.add_all([m1, m1_meta, m2, m2_meta])
            session.commit()

    def test_strict_temporal_isolation(self):
        generator = CricketStatsGenerator(self.engine)
        
        # Create the domain model for the PAST match (2019-05-10)
        past_match = CricketEvent(
            id="match_1",
            date=datetime(2019, 5, 10),
            location="v1",
            participants=["team_ind", "team_aus"],
            match_type="ODI",
            venue_name="Venue 1",
            team_a="team_ind",
            team_b="team_aus"
        )
        
        features = generator.generate(past_match)
        
        # Team India won Match 1, but this result AND Match 2's result MUST NOT 
        # be in the historical record because `events.date < event.date` is strictly enforced.
        # So for match 1, there is NO historical record of Team India playing Team Aus yet.
        # The generator should return the default 50% (0.5) because history is empty.
        
        self.assertEqual(features["stat_team_a_win_pct_all"], 0.5)
        self.assertEqual(features["stat_team_b_win_pct_all"], 0.5)
        self.assertEqual(features["stat_h2h_team_a_win_pct"], 0.5)
        
        # Now let's calculate for Match 2
        future_match = CricketEvent(
            id="match_2",
            date=datetime(2019, 5, 15),
            location="v1",
            participants=["team_ind", "team_aus"],
            match_type="ODI",
            venue_name="Venue 1",
            team_a="team_ind",
            team_b="team_aus"
        )
        
        features_2 = generator.generate(future_match)
        
        # For Match 2, Match 1 (where India won) is strictly in the past.
        # Therefore India's win rate should be 1.0 (1 win / 1 match).
        self.assertEqual(features_2["stat_team_a_win_pct_all"], 1.0)
        
        # Australia lost match 1, so their win rate should be 0.0 (0 wins / 1 match).
        self.assertEqual(features_2["stat_team_b_win_pct_all"], 0.0)

if __name__ == '__main__':
    unittest.main()
