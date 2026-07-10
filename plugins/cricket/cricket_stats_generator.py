from typing import Dict, Any
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import Session
from plugins.cricket.cricket_event import CricketEvent
from core.generators.base_generator import BaseFeatureGenerator
from core.models.base_event import BaseEvent
from core.memory.schema import DBEvent, DBCricketMatchMetadata

from datetime import datetime, date

def _to_dt(val):
    if val is None:
        return datetime.min
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val[:19])
        except Exception:
            return datetime.min
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day)
    return datetime.min

class CricketStatsGenerator(BaseFeatureGenerator):
    """
    Generates domain-specific statistical features for a cricket match.
    Uses strict temporal filtering (`date < current_date`) to prevent data leakage.
    History is loaded once via direct SQL JOIN (events + cricket_match_metadata) and
    indexed by sorted date for O(log n) temporal filtering using bisect.
    """
    
    def __init__(self, engine):
        self.engine = engine
        self._all_history = None
        self._history_dates = None  # Parallel sorted list of dates for bisect

    @property
    def generator_name(self) -> str:
        return "CricketStatsGenerator"

    def generate(self, event: BaseEvent) -> Dict[str, float]:
        """
        Calculates historical statistical features.
        """
        if not isinstance(event, CricketEvent):
            raise ValueError("CricketStatsGenerator requires a CricketEvent")
            
        # ── OPTIMIZATION: Load all history into memory ONCE ──
        if self._all_history is None:
            if hasattr(self.engine, 'connect') or (isinstance(self.engine, str) and self.engine.startswith('postgresql://')):
                from sqlalchemy.orm import Session
                from sqlalchemy import select, desc
                from core.memory.schema import DBEvent, DBCricketMatchMetadata, get_engine
                engine_obj = get_engine(self.engine) if isinstance(self.engine, str) else self.engine
                with Session(engine_obj) as session:
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
                            "date": _to_dt(e.date),
                            "venue_id": e.venue_id,
                            "outcome": e.outcome,
                            "team_a_id": m.team_a_id,
                            "team_b_id": m.team_b_id
                        })
            elif hasattr(self.engine, 'table'):
                # Supabase PostgREST client passed.
                # CRITICAL: Do NOT use prediction_store here — it has NULL team_a/team_b.
                # CRITICAL: Do NOT use REST API with limit= — Supabase caps all responses at
                #           1000 rows regardless of the limit parameter, causing all history
                #           lookups to return 0 matches and all features to default to 0.5.
                # FIX: Use psycopg2 direct SQL to JOIN events + cricket_match_metadata.
                import os
                import psycopg2 as _pg2
                _db_url = os.environ.get("SUPABASE_DB_URL")
                if _db_url:
                    try:
                        _conn = _pg2.connect(_db_url)
                        _cur = _conn.cursor()
                        _cur.execute("""
                            SELECT e.date, e.venue_id, e.outcome, m.team_a_id, m.team_b_id
                            FROM events e
                            JOIN cricket_match_metadata m ON m.event_id = e.id
                            WHERE e.outcome IS NOT NULL
                              AND e.event_type = 'cricket'
                              AND m.team_a_id IS NOT NULL
                              AND m.team_b_id IS NOT NULL
                            ORDER BY e.date ASC
                        """)
                        rows = _cur.fetchall()
                        _conn.close()
                        self._all_history = [
                            {
                                "date": _to_dt(row[0]),
                                "venue_id": row[1],
                                "outcome": row[2],
                                "team_a_id": row[3],
                                "team_b_id": row[4],
                            }
                            for row in rows
                        ]
                    except Exception as _e:
                        import logging as _log
                        _log.warning(f"CricketStatsGenerator: direct SQL history load failed: {_e}. Falling back to empty history.")
                        self._all_history = []
                else:
                    import logging as _log
                    _log.warning("CricketStatsGenerator: SUPABASE_DB_URL not set, history will be empty.")
                    self._all_history = []
            else:
                self._all_history = []

        # Build sorted date index once after history is loaded (for O(log n) filtering)
        if self._history_dates is None and self._all_history:
            import bisect as _bisect_mod
            self._history_dates = [r["date"] for r in self._all_history]
            self._bisect = _bisect_mod

        # Filter strictly before current event date using bisect (O(log n) per call)
        event_dt = _to_dt(event.date)
        if self._history_dates:
            import bisect as _bisect
            cutoff = _bisect.bisect_left(self._history_dates, event_dt)
            historical_records = self._all_history[:cutoff]
        else:
            historical_records = [r for r in self._all_history if r["date"] < event_dt]

        features = {}

        def calc_win_pct(team_id: str, limit: int = None) -> float:
            team_matches = [
                m for m in historical_records 
                if m["team_a_id"] == team_id or m["team_b_id"] == team_id
            ]
            if limit is not None and limit > 0:
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
        
        # True iterative Elo rating calculation up to event.date
        elos = {}
        sorted_history = sorted([r for r in historical_records if r["outcome"] and r["team_a_id"] and r["team_b_id"]], key=lambda x: x["date"])
        for r in sorted_history:
            ta = r["team_a_id"]
            tb = r["team_b_id"]
            out = r["outcome"]
            ra = elos.get(ta, 1500.0)
            rb = elos.get(tb, 1500.0)
            ea = 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
            eb = 1.0 - ea
            sa = 1.0 if out == ta else (0.0 if out == tb else 0.5)
            sb = 1.0 - sa
            k = 32.0
            elos[ta] = ra + k * (sa - ea)
            elos[tb] = rb + k * (sb - eb)
            
        features["stat_team_a_elo"] = round(elos.get(team_a, 1500.0), 2)
        features["stat_team_b_elo"] = round(elos.get(team_b, 1500.0), 2)
        
        return features
