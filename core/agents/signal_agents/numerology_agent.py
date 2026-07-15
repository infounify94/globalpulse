"""
Phase 9 Signal Agent: Numerology Features.
Pure mathematical transformations - no external APIs required.

Features produced:
    date_digit_sum          : Sum of all digits in YYYYMMDD (e.g. 2023-04-15 -> 17)
    date_master_number      : Reduce digit_sum to single digit (17 -> 1+7 = 8)
    team1_gematria          : Simple A=1..Z=26 sum for team1 name
    team2_gematria          : Simple A=1..Z=26 sum for team2 name
    match_number_vibration  : match_id % 9 + 1  (numerological vibration 1-9)

All values are int or float - CatBoost compatible.
"""

import re
from typing import Dict, Any, Union


def _digit_sum(n: int) -> int:
    """Sum all digits of an integer."""
    return sum(int(d) for d in str(abs(n)))


def _reduce_to_single(n: int) -> int:
    """Repeatedly sum digits until a single digit is reached (Pythagorean reduction)."""
    while n >= 10:
        n = _digit_sum(n)
    return n


def _gematria(name: str) -> int:
    """
    Simple Pythagorean gematria: A=1, B=2, ..., Z=26.
    Non-alphabetic characters (spaces, underscores, hyphens) are ignored.
    """
    total = 0
    for ch in name.upper():
        if ch.isalpha():
            total += ord(ch) - ord('A') + 1
    return total


class NumerologyAgent:
    """
    Derives numerological features from match metadata.
    Completely stateless - no caching needed.
    """

    def compute_features(
        self,
        match_date_str: str,
        team1: str,
        team2: str,
        match_id: Union[str, int, None] = None,
    ) -> Dict[str, float]:
        """
        Parameters
        ----------
        match_date_str : str
            Date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' format.
        team1 : str
            Name of team 1.
        team2 : str
            Name of team 2.
        match_id : str | int | None
            Match identifier. Numeric portion extracted for vibration calc.

        Returns
        -------
        Dict[str, float]
            Numerology feature dict. Always non-empty (all computations are pure math).
        """
        features: Dict[str, float] = {}

        # ---------------------------------------------------------------
        # 1. Date Digit Sum  (YYYYMMDD)
        # ---------------------------------------------------------------
        try:
            date_compact = str(match_date_str)[:10].replace("-", "")  # '20230415'
            if len(date_compact) == 8 and date_compact.isdigit():
                dsum = sum(int(ch) for ch in date_compact)
                features["date_digit_sum"] = float(dsum)
                features["date_master_number"] = float(_reduce_to_single(dsum))
        except Exception:
            features["date_digit_sum"] = 0.0
            features["date_master_number"] = 0.0

        # ---------------------------------------------------------------
        # 2. Team Name Gematria
        # ---------------------------------------------------------------
        try:
            features["team1_gematria"] = float(_gematria(str(team1)))
        except Exception:
            features["team1_gematria"] = 0.0

        try:
            features["team2_gematria"] = float(_gematria(str(team2)))
        except Exception:
            features["team2_gematria"] = 0.0

        # ---------------------------------------------------------------
        # 3. Match Number Vibration
        # ---------------------------------------------------------------
        try:
            if match_id is not None:
                # Extract the numeric portion from match_id (e.g. 'match_1234' -> 1234)
                numeric_str = re.sub(r"[^0-9]", "", str(match_id))
                if numeric_str:
                    match_num = int(numeric_str)
                    features["match_number_vibration"] = float(match_num % 9 + 1)
                else:
                    features["match_number_vibration"] = 1.0
            else:
                features["match_number_vibration"] = 1.0
        except Exception:
            features["match_number_vibration"] = 1.0

        return features


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    agent = NumerologyAgent()

    # 2011 World Cup Final: India vs Sri Lanka, 2011-04-02
    feats = agent.compute_features(
        match_date_str="2011-04-02",
        team1="India",
        team2="Sri Lanka",
        match_id="match_336015",
    )
    print("2011 WC Final features:")
    for k, v in feats.items():
        print(f"  {k}: {v}")

    # Expected:
    # date_compact = "20110402"  -> 2+0+1+1+0+4+0+2 = 10
    # date_master_number = 1+0 = 1
    # India gematria: I=9, N=14, D=4, I=9, A=1 -> 37
    # Sri Lanka gematria: S=19,R=18,I=9,L=12,A=1,N=14,K=11,A=1 -> 85
    print("\n2023-04-15 demo:")
    feats2 = agent.compute_features("2023-04-15", "Mumbai Indians", "Chennai Super Kings", "1234567")
    for k, v in feats2.items():
        print(f"  {k}: {v}")
