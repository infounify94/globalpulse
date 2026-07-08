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
        self._all_history = None

    @property
    def generator_name(self) -> str:
        return "CricketStatsGenerator"

    def generate(self, event: BaseEvent) -> Dict[str, float]:
        """
        Calculates historical statistical features.
        """
        if not isinstance(event, CricketEvent):
            raise ValueError("CricketStatsGenerator requires a CricketEvent")
            
        # ── OPTIMIZATION: Load all history into memory ONCE (takes ~1-2 seconds) ──
        if self._all_history is None:
            with Session(self.engine) as session:
                stmt = (
                    select(DBEvent, DBCricketMatchMetadata)
                    .join(DBCricketMatchMetadata)
                    .where(DBEvent.event_type == 'cricket')
                    .order_by(desc(DBEvent.date))
                )
                raw_records = session.execute(stmt).all()
                self._all_history = []
                for e, m in raw_records:
                    self._all_history.append({
                        "date": e.date,
                        "venue_id": e.venue_id,
                        "outcome": e.outcome,
                        "team_a_id": m.team_a_id,
                        "team_b_id": m.team_b_id
                    })
                    
        # Filter strictly before current event date in-memory
        historical_records = [
            r for r in self._all_history if r["date"] < event.date
        ]

        features = {}

        def calc_win_pct(team_id: str, limit: int = None) -> float:
            team_matches = [
                m for m in historical_records 
                if m["team_a_id"] == team_id or m["team_b_id"] == team_id
            ]
            if limit:
                team_matches = team_matches[:limit]
            if not team_matches:
                return 0.5
            wins = sum(1 for m in team_matches if m["outcome"] == team_id)
            return wins / len(team_matches)
            
        def calc_h2h(team_id: str, opp_id: str) -> float:
            h2h_matches = [
                m for m in historical_records 
                if (m["team_a_id"] == team_id and m["team_b_id"] == opp_id) or 
                   (m["team_a_id"] == opp_id and m["team_b_id"] == team_id)
            ]
            if not h2h_matches:
                return 0.5
            wins = sum(1 for m in h2h_matches if m["outcome"] == team_id)
            return wins / len(h2h_matches)
            
        def calc_venue_pct(team_id: str, venue_id: str) -> float:
            venue_matches = [
                m for m in historical_records 
                if m["venue_id"] == venue_id and (m["team_a_id"] == team_id or m["team_b_id"] == team_id)
            ]
            if not venue_matches:
                return 0.5
            wins = sum(1 for m in venue_matches if m["outcome"] == team_id)
            return wins / len(venue_matches)

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
        
        features["stat_team_a_elo"] = 1500.0 + (features["stat_team_a_win_pct_all"] - 0.5) * 400
        features["stat_team_b_elo"] = 1500.0 + (features["stat_team_b_win_pct_all"] - 0.5) * 400
        
        return features
