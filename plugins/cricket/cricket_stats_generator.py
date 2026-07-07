from typing import Dict, Any
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import Session
from plugins.cricket.cricket_event import CricketEvent
from core.generators.base_generator import BaseFeatureGenerator
from core.models.base_event import BaseEvent
from core.memory.schema import DBEvent, DBCricketMatchMetadata

class CricketStatsGenerator(BaseFeatureGenerator):
    """
    Generates domain-specific statistical features for a cricket match.
    Uses strict temporal filtering (`date < current_date`) to prevent data leakage.
    """
    
    def __init__(self, engine):
        self.engine = engine

    @property
    def generator_name(self) -> str:
        return "CricketStatsGenerator"

    def generate(self, event: BaseEvent) -> Dict[str, float]:
        """
        Calculates historical statistical features.
        """
        if not isinstance(event, CricketEvent):
            raise ValueError("CricketStatsGenerator requires a CricketEvent")
            
        features = {}
        
        with Session(self.engine) as session:
            # Get historical matches STRICTLY BEFORE the current event date
            # This is the ironclad anti-leakage guarantee
            stmt = (
                select(DBEvent, DBCricketMatchMetadata)
                .join(DBCricketMatchMetadata)
                .where(DBEvent.event_type == 'cricket')
                .where(DBEvent.date < event.date)
                .order_by(desc(DBEvent.date))
            )
            historical_records = session.execute(stmt).all()
            
            # Helper to calculate win percentage
            def calc_win_pct(team_id: str, limit: int = None) -> float:
                team_matches = [
                    (e, m) for e, m in historical_records 
                    if m.team_a_id == team_id or m.team_b_id == team_id
                ]
                if limit:
                    team_matches = team_matches[:limit]
                    
                if not team_matches:
                    return 0.5 # Default to 50% if no history
                    
                wins = sum(1 for e, m in team_matches if e.outcome == team_id)
                return wins / len(team_matches)
                
            # Helper for H2H
            def calc_h2h(team_id: str, opp_id: str) -> float:
                h2h_matches = [
                    (e, m) for e, m in historical_records 
                    if (m.team_a_id == team_id and m.team_b_id == opp_id) or 
                       (m.team_a_id == opp_id and m.team_b_id == team_id)
                ]
                if not h2h_matches:
                    return 0.5
                wins = sum(1 for e, m in h2h_matches if e.outcome == team_id)
                return wins / len(h2h_matches)
                
            # Helper for Venue Win Pct
            def calc_venue_pct(team_id: str, venue_id: str) -> float:
                venue_matches = [
                    (e, m) for e, m in historical_records 
                    if e.venue_id == venue_id and (m.team_a_id == team_id or m.team_b_id == team_id)
                ]
                if not venue_matches:
                    return 0.5
                wins = sum(1 for e, m in venue_matches if e.outcome == team_id)
                return wins / len(venue_matches)

            # Generate Features
            team_a = event.team_a
            team_b = event.team_b
            venue = event.location
            
            features["stat_team_a_win_pct_5"] = calc_win_pct(team_a, 5)
            features["stat_team_a_win_pct_10"] = calc_win_pct(team_a, 10)
            features["stat_team_a_win_pct_all"] = calc_win_pct(team_a)
            
            features["stat_team_b_win_pct_5"] = calc_win_pct(team_b, 5)
            features["stat_team_b_win_pct_10"] = calc_win_pct(team_b, 10)
            features["stat_team_b_win_pct_all"] = calc_win_pct(team_b)
            
            features["stat_h2h_team_a_win_pct"] = calc_h2h(team_a, team_b)
            
            features["stat_venue_team_a_win_pct"] = calc_venue_pct(team_a, venue)
            features["stat_venue_team_b_win_pct"] = calc_venue_pct(team_b, venue)
            
            # Simple Elo calculation proxy based on historical streak
            # A full chronological Elo requires a global state tracker, which we approximate 
            # here for the local scope, or we'd build a separate Elo Engine.
            # Let's add basic Elo stubs.
            features["stat_team_a_elo"] = 1500.0 + (features["stat_team_a_win_pct_all"] - 0.5) * 400
            features["stat_team_b_elo"] = 1500.0 + (features["stat_team_b_win_pct_all"] - 0.5) * 400
            
        return features
