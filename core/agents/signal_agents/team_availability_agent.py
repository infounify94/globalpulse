class TeamAvailabilityAgent:
    """
    Analyzes the confirmed Playing XI against the historical roster to detect
    missing star players, injured players, or rested captains.
    """
    def __init__(self):
        pass

    def check_availability(self, expected_xi, confirmed_xi):
        """
        Returns a penalty modifier if key players are missing from the confirmed XI.
        """
        missing_players = set(expected_xi) - set(confirmed_xi)
        penalty = 0.0
        missing_stars = []

        # Simplified logic for Phase 11 MVP
        if len(missing_players) > 0:
            penalty = len(missing_players) * -0.05
            missing_stars = list(missing_players)

        return {
            "missing_count": len(missing_players),
            "missing_players": missing_stars,
            "team_strength_modifier": 1.0 + penalty,
            "has_injury_impact": len(missing_players) >= 2
        }
