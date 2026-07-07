import json
import logging
import os
from datetime import datetime
from typing import Tuple, List, Optional

from core.memory.schema import (
    DBEvent, DBCricketMatchMetadata, DBTeam, DBVenue, DBInning, DBDelivery
)


class CricsheetParser:
    """
    Parses Cricsheet JSON files (v2 format: innings[].overs[].deliveries[]).
    Handles both old (innings[].deliveries[]) and new (innings[].overs[]) formats.
    """

    def parse(self, filepath: str) -> Tuple:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        info = data.get('info', {})
        innings_data = data.get('innings', [])

        # ── Match Metadata ─────────────────────────────────────────────────
        match_type = info.get('match_type', 'unknown').upper()
        dates = info.get('dates', [])
        if not dates:
            raise ValueError(f"No dates in {filepath}")

        match_date = datetime.strptime(dates[0], "%Y-%m-%d")
        teams = info.get('teams', [])
        if len(teams) < 2:
            raise ValueError(f"Not enough teams in {filepath}")

        team_a_name, team_b_name = teams[0], teams[1]
        venue_name = info.get('venue', 'Unknown Venue')
        city = info.get('city', None)

        toss = info.get('toss', {})
        toss_winner = toss.get('winner')
        toss_decision = toss.get('decision')

        outcome = info.get('outcome', {})
        winner = outcome.get('winner')  # None for no-result/tie/draw

        event_id = os.path.basename(filepath).replace('.json', '')

        # ── Teams ──────────────────────────────────────────────────────────
        db_team_a = DBTeam(id=self._slug(team_a_name), name=team_a_name, domain="cricket")
        db_team_b = DBTeam(id=self._slug(team_b_name), name=team_b_name, domain="cricket")

        # ── Venue ──────────────────────────────────────────────────────────
        venue_id = self._slug(venue_name)
        db_venue = DBVenue(id=venue_id, name=venue_name, city=city)

        # ── Event ──────────────────────────────────────────────────────────
        db_event = DBEvent(
            id=event_id,
            event_type="cricket",
            date=match_date,
            venue_id=venue_id,
            outcome=self._slug(winner) if winner else None
        )

        # ── Cricket Metadata ───────────────────────────────────────────────
        db_metadata = DBCricketMatchMetadata(
            event_id=event_id,
            match_type=match_type,
            toss_winner_id=self._slug(toss_winner) if toss_winner else None,
            toss_decision=toss_decision,
            team_a_id=db_team_a.id,
            team_b_id=db_team_b.id
        )

        # ── Innings & Deliveries ───────────────────────────────────────────
        db_innings = []
        db_deliveries = []

        for idx, inn_dict in enumerate(innings_data):
            batting_team = inn_dict.get('team', team_a_name if idx % 2 == 0 else team_b_name)
            bowling_team = team_b_name if batting_team == team_a_name else team_a_name

            inning_id = f"{event_id}_inn_{idx + 1}"
            db_inning = DBInning(
                id=inning_id,
                event_id=event_id,
                inning_number=idx + 1,
                batting_team_id=self._slug(batting_team),
                bowling_team_id=self._slug(bowling_team),
                total_runs=0,
                total_wickets=0
            )

            # ── NEW FORMAT: innings[].overs[].deliveries[] ────────────────
            overs = inn_dict.get('overs', [])
            if overs:
                for over_obj in overs:
                    over_num = over_obj.get('over', 0)
                    deliveries = over_obj.get('deliveries', [])
                    for ball_num, delivery in enumerate(deliveries, start=1):
                        self._parse_delivery_v2(
                            delivery, inning_id, over_num, ball_num,
                            db_inning, db_deliveries
                        )

            # ── OLD FORMAT: innings[key].deliveries[{over.ball: {...}}] ───
            else:
                old_deliveries = inn_dict.get('deliveries', [])
                for del_wrapper in old_deliveries:
                    if isinstance(del_wrapper, dict):
                        for over_ball, del_details in del_wrapper.items():
                            try:
                                over_str, ball_str = str(over_ball).split('.')
                                over_num, ball_num = int(over_str), int(ball_str)
                            except (ValueError, AttributeError):
                                continue
                            self._parse_delivery_v1(
                                del_details, inning_id, over_num, ball_num,
                                db_inning, db_deliveries
                            )

            db_innings.append(db_inning)

        return db_event, db_metadata, [db_team_a, db_team_b], db_venue, db_innings, db_deliveries

    def _parse_delivery_v2(self, delivery: dict, inning_id: str,
                           over_num: int, ball_num: int,
                           db_inning: DBInning, db_deliveries: list):
        """Handles the current Cricsheet v2 format."""
        batter  = delivery.get('batter', 'unknown')
        bowler  = delivery.get('bowler', 'unknown')
        runs    = delivery.get('runs', {})
        runs_batter = runs.get('batter', 0)
        runs_extras = runs.get('extras', 0)

        wickets = delivery.get('wickets', [])
        is_wicket   = len(wickets) > 0
        wicket_type = wickets[0].get('kind') if is_wicket else None

        db_inning.total_runs += (runs_batter + runs_extras)
        if is_wicket:
            db_inning.total_wickets += 1

        db_delivery = DBDelivery(
            id=f"{inning_id}_{over_num}_{ball_num}",
            inning_id=inning_id,
            over_number=over_num,
            ball_number=ball_num,
            batter_id=self._slug(batter),
            bowler_id=self._slug(bowler),
            runs_batter=runs_batter,
            runs_extras=runs_extras,
            is_wicket=is_wicket,
            wicket_type=wicket_type
        )
        db_deliveries.append(db_delivery)

    def _parse_delivery_v1(self, del_details: dict, inning_id: str,
                           over_num: int, ball_num: int,
                           db_inning: DBInning, db_deliveries: list):
        """Handles the old Cricsheet v1 format."""
        batter  = del_details.get('batsman', 'unknown')
        bowler  = del_details.get('bowler', 'unknown')
        runs    = del_details.get('runs', {})
        runs_batter = runs.get('batsman', 0)
        runs_extras = runs.get('extras', 0)

        is_wicket   = 'wicket' in del_details
        wicket_type = del_details['wicket'].get('kind') if is_wicket else None

        db_inning.total_runs += (runs_batter + runs_extras)
        if is_wicket:
            db_inning.total_wickets += 1

        db_delivery = DBDelivery(
            id=f"{inning_id}_{over_num}_{ball_num}",
            inning_id=inning_id,
            over_number=over_num,
            ball_number=ball_num,
            batter_id=self._slug(batter),
            bowler_id=self._slug(bowler),
            runs_batter=runs_batter,
            runs_extras=runs_extras,
            is_wicket=is_wicket,
            wicket_type=wicket_type
        )
        db_deliveries.append(db_delivery)

    @staticmethod
    def _slug(name: Optional[str]) -> str:
        if not name:
            return "unknown"
        return name.lower().replace(' ', '_').replace('-', '_').replace("'", "")
