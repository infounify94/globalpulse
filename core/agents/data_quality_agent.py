class DataQualityAgent:
    """
    Gatekeeper that verifies all Live Data requirements before allowing the Engine to predict.
    """
    def __init__(self):
        pass

    def verify_live_match(self, match_data):
        """
        Takes live match data and checks if it's safe to predict.
        Returns (is_valid, reason, recommendation_status)
        """
        if not match_data:
            return False, "Missing match data object", "ERROR"

        playing_xi = match_data.get("playing_xi", [])
        if len(playing_xi) < 22:
            return False, f"Playing XI incomplete ({len(playing_xi)}/22)", "Waiting for Playing XI"

        toss_winner = match_data.get("toss_winner")
        if not toss_winner:
            return False, "Toss not yet completed", "Waiting for Toss"

        match_status = match_data.get("status", "upcoming")
        if match_status == "abandoned":
            return False, "Match abandoned", "SKIP"

        return True, "Data pristine", "READY"
