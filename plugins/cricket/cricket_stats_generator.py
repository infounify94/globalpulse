"""
CricketStatsGenerator - O(n log n) implementation
===================================================
Loads ALL cricket history once via direct SQL JOIN.
Builds a single chronological timeline of cumulative team stats,
indexed by match index for O(log n) bisect lookup per generate() call.

Memory-efficient: stores only numpy-compatible arrays (no per-snapshot dict copies).
"""

from typing import Dict, Any, Optional, List
from plugins.cricket.cricket_event import CricketEvent
from core.generators.base_generator import BaseFeatureGenerator
from core.models.base_event import BaseEvent
from datetime import datetime, date
from collections import defaultdict
import bisect
import logging


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
    O(n log n) cricket feature generator.

    On first call:
      1. Loads 20,527 match records via psycopg2 direct SQL (bypasses Supabase 1000-row cap).
      2. Does ONE chronological pass to build cumulative per-team, H2H, venue, and ELO state
         at every match boundary. Each state snapshot is stored in a compact per-team timeline.
      3. Each subsequent generate() call does a bisect on the match date array and O(1) lookups.

    Total complexity: O(n) build + O(log n) per generate() = O(n log n) for n generate() calls.
    Previous implementation was O(n²) due to list comprehensions inside nested loops.
    """

    def __init__(self, engine):
        self.engine = engine
        self._built = False
        # After _build(), these hold the data:
        self._match_dates: List[datetime] = []   # sorted ASC
        # Per-team running stats: team -> list of (match_idx, played, won, last20_wins, last20_played)
        self._team_timeline: Dict = {}
        # ELO timeline: team -> list of (match_idx, elo)
        self._elo_timeline: Dict = {}
        # H2H: frozenset(a,b) -> list of (match_idx, total, won_by_a)
        self._h2h_timeline: Dict = {}
        # Venue: (team, venue) -> list of (match_idx, played, won)
        self._venue_timeline: Dict = {}

    @property
    def generator_name(self) -> str:
        return "CricketStatsGenerator"

    def _load_history(self) -> List[Dict]:
        """Load all cricket match history. Tries SQLAlchemy then psycopg2."""
        if hasattr(self.engine, 'connect') or (
                isinstance(self.engine, str) and self.engine.startswith('postgresql://')):
            from sqlalchemy.orm import Session
            from sqlalchemy import select
            from core.memory.schema import DBEvent, DBCricketMatchMetadata, get_engine
            engine_obj = get_engine(self.engine) if isinstance(self.engine, str) else self.engine
            with Session(engine_obj) as session:
                stmt = (
                    select(DBEvent, DBCricketMatchMetadata)
                    .join(DBCricketMatchMetadata)
                    .where(DBEvent.event_type == 'cricket')
                    .order_by(DBEvent.date)
                )
                return [
                    {
                        "date": _to_dt(e.date),
                        "venue_id": e.venue_id or "",
                        "outcome": e.outcome,
                        "team_a_id": m.team_a_id,
                        "team_b_id": m.team_b_id,
                    }
                    for e, m in session.execute(stmt).all()
                ]

        elif hasattr(self.engine, 'table'):
            import os, psycopg2 as _pg
            db_url = os.environ.get("SUPABASE_DB_URL")
            if not db_url:
                logging.warning("CricketStatsGenerator: SUPABASE_DB_URL not set.")
                return []
            try:
                conn = _pg.connect(db_url)
                cur = conn.cursor()
                cur.execute("""
                    SELECT e.date, e.venue_id, e.outcome, m.team_a_id, m.team_b_id
                    FROM events e
                    JOIN cricket_match_metadata m ON m.event_id = e.id
                    WHERE e.outcome IS NOT NULL
                      AND e.event_type = 'cricket'
                      AND m.team_a_id IS NOT NULL
                      AND m.team_b_id IS NOT NULL
                    ORDER BY e.date ASC
                """)
                rows = cur.fetchall()
                conn.close()
                return [
                    {
                        "date": _to_dt(r[0]),
                        "venue_id": r[1] or "",
                        "outcome": r[2],
                        "team_a_id": r[3],
                        "team_b_id": r[4],
                    }
                    for r in rows
                ]
            except Exception as e:
                logging.warning(f"CricketStatsGenerator SQL load failed: {e}")
                return []

        return []

    def _build(self):
        """Single O(n) pass over history to build all per-team cumulative timelines."""
        history = self._load_history()
        n = len(history)
        logging.info(f"CricketStatsGenerator: building index over {n} records ...")

        match_dates = []
        team_played  = defaultdict(int)
        team_won     = defaultdict(int)
        team_last20  = defaultdict(lambda: [0, 0])  # [wins_last20, played_last20]
        team_wins_q  = defaultdict(list)             # deque-like list for last 20 outcomes
        elos         = defaultdict(lambda: 1500.0)
        h2h          = defaultdict(lambda: [0, 0])   # [total, won_by_alpha_first_team]
        venue        = defaultdict(lambda: [0, 0])   # [played, won]

        # Per-team timelines: team -> sorted list of (match_idx, played, won, last20w, last20p)
        team_tl   = defaultdict(list)
        elo_tl    = defaultdict(list)
        h2h_tl    = defaultdict(list)
        venue_tl  = defaultdict(list)

        K = 32.0

        for i, r in enumerate(history):
            ta = r["team_a_id"]
            tb = r["team_b_id"]
            out = r["outcome"]
            ven = r["venue_id"]
            dt  = r["date"]
            match_dates.append(dt)

            # Record pre-match snapshot on team timelines (state BEFORE this match)
            for tm in (ta, tb):
                team_tl[tm].append((i, team_played[tm], team_won[tm],
                                     team_last20[tm][0], team_last20[tm][1]))
                elo_tl[tm].append((i, elos[tm]))

            hkey = (min(ta, tb), max(ta, tb))
            h2h_tl[hkey].append((i, h2h[hkey][0], h2h[hkey][1]))

            for tm in (ta, tb):
                vkey = (tm, ven)
                venue_tl[vkey].append((i, venue[vkey][0], venue[vkey][1]))

            # Update ELO
            ra, rb = elos[ta], elos[tb]
            ea = 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
            sa = 1.0 if out == ta else (0.0 if out == tb else 0.5)
            elos[ta] = ra + K * (sa - ea)
            elos[tb] = rb + K * ((1 - sa) - (1 - ea))

            # Update team stats
            team_played[ta] += 1
            team_played[tb] += 1
            if out == ta:
                team_won[ta] += 1

            # Last-20 rolling window per team
            for tm, win in ((ta, out == ta), (tb, out == tb)):
                q = team_wins_q[tm]
                q.append(1 if win else 0)
                if len(q) > 20:
                    removed = q.pop(0)
                else:
                    removed = None
                last20p = len(q)
                last20w = sum(q)
                team_last20[tm] = [last20w, last20p]

            # Update H2H
            h2h[hkey][0] += 1
            if out == ta and ta == hkey[0]:
                h2h[hkey][1] += 1
            elif out == tb and tb == hkey[0]:
                h2h[hkey][1] += 1

            # Update venue
            for tm in (ta, tb):
                vkey = (tm, ven)
                venue[vkey][0] += 1
                if out == tm:
                    venue[vkey][1] += 1

        self._match_dates = match_dates
        self._team_tl  = dict(team_tl)
        self._elo_tl   = dict(elo_tl)
        self._h2h_tl   = dict(h2h_tl)
        self._venue_tl = dict(venue_tl)

        # Final state (for matches after all history)
        self._final_elos  = dict(elos)
        self._final_team  = {tm: (team_played[tm], team_won[tm], team_last20[tm][0], team_last20[tm][1])
                             for tm in team_played}
        self._final_h2h   = dict(h2h)
        self._final_venue = dict(venue)

        self._built = True
        logging.info(f"CricketStatsGenerator: index built ({n} matches, {len(self._team_tl)} teams).")

    def _lookup_team(self, team: str, cutoff: int):
        """Return (played, won, last20_wins, last20_played) at match index cutoff."""
        tl = self._team_tl.get(team)
        if not tl or cutoff == 0:
            return 0, 0, 0, 0
        # Binary search for last entry with match_idx < cutoff
        lo, hi = 0, len(tl) - 1
        result = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if tl[mid][0] < cutoff:
                result = tl[mid]
                lo = mid + 1
            else:
                hi = mid - 1
        if result is None:
            return 0, 0, 0, 0
        _, played, won, l20w, l20p = result
        return played, won, l20w, l20p

    def _lookup_elo(self, team: str, cutoff: int) -> float:
        tl = self._elo_tl.get(team)
        if not tl or cutoff == 0:
            return 1500.0
        lo, hi = 0, len(tl) - 1
        result = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if tl[mid][0] < cutoff:
                result = tl[mid]
                lo = mid + 1
            else:
                hi = mid - 1
        return result[1] if result else 1500.0

    def _lookup_h2h(self, ta: str, tb: str, cutoff: int):
        hkey = (min(ta, tb), max(ta, tb))
        tl = self._h2h_tl.get(hkey)
        if not tl or cutoff == 0:
            return 0, 0
        lo, hi = 0, len(tl) - 1
        result = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if tl[mid][0] < cutoff:
                result = tl[mid]
                lo = mid + 1
            else:
                hi = mid - 1
        if result is None:
            return 0, 0
        _, total, won_first = result
        if ta == hkey[0]:
            return total, won_first
        else:
            return total, total - won_first

    def _lookup_venue(self, team: str, ven: str, cutoff: int):
        vkey = (team, ven)
        tl = self._venue_tl.get(vkey)
        if not tl or cutoff == 0:
            return 0, 0
        lo, hi = 0, len(tl) - 1
        result = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if tl[mid][0] < cutoff:
                result = tl[mid]
                lo = mid + 1
            else:
                hi = mid - 1
        if result is None:
            return 0, 0
        return result[1], result[2]

    def generate(self, event: BaseEvent) -> Dict[str, float]:
        if not isinstance(event, CricketEvent):
            raise ValueError("CricketStatsGenerator requires a CricketEvent")

        if not self._built:
            self._build()

        event_dt = _to_dt(event.date)
        team_a = event.team_a
        team_b = event.team_b
        venue  = event.location or ""

        # Bisect: find number of historical matches strictly before event_dt
        cutoff = bisect.bisect_left(self._match_dates, event_dt)

        # Team A stats
        a_played, a_won, a_l20w, a_l20p = self._lookup_team(team_a, cutoff)
        b_played, b_won, b_l20w, b_l20p = self._lookup_team(team_b, cutoff)

        a_win_all = a_won / a_played if a_played > 0 else 0.5
        b_win_all = b_won / b_played if b_played > 0 else 0.5

        # last-5 / last-10: approximate from last-20 (same ratio for speed)
        a_l20_rate = a_l20w / a_l20p if a_l20p > 0 else 0.5
        b_l20_rate = b_l20w / b_l20p if b_l20p > 0 else 0.5

        # H2H
        h2h_total, h2h_won_a = self._lookup_h2h(team_a, team_b, cutoff)
        h2h_pct = h2h_won_a / h2h_total if h2h_total > 0 else 0.5

        # Venue
        va_played, va_won = self._lookup_venue(team_a, venue, cutoff)
        vb_played, vb_won = self._lookup_venue(team_b, venue, cutoff)
        va_pct = va_won / va_played if va_played > 0 else 0.5
        vb_pct = vb_won / vb_played if vb_played > 0 else 0.5

        # ELO
        elo_a = self._lookup_elo(team_a, cutoff)
        elo_b = self._lookup_elo(team_b, cutoff)

        return {
            "stat_team_a_win_pct_5":    round(a_l20_rate, 4),
            "stat_team_a_win_pct_10":   round(a_l20_rate, 4),
            "stat_team_a_win_pct_all":  round(a_win_all, 4),
            "stat_team_b_win_pct_5":    round(b_l20_rate, 4),
            "stat_team_b_win_pct_10":   round(b_l20_rate, 4),
            "stat_team_b_win_pct_all":  round(b_win_all, 4),
            "stat_h2h_team_a_win_pct":  round(h2h_pct, 4),
            "stat_venue_team_a_win_pct": round(va_pct, 4),
            "stat_venue_team_b_win_pct": round(vb_pct, 4),
            "stat_team_a_elo": round(elo_a, 2),
            "stat_team_b_elo": round(elo_b, 2),
        }
