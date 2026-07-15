import pandas as pd
import numpy as np
from typing import Dict

class SportsMathAgent:
    """
    Pillar 1: Calculates traditional sports mathematics to establish a strong baseline.
    Calculates Dynamic ELO, Rolling Momentum, and Head-to-Head dominance without data leakage.
    Must be run on a chronologically sorted dataframe.
    """
    def __init__(self, base_elo: float = 1500.0, k_factor: float = 32.0):
        self.base_elo = base_elo
        self.k_factor = k_factor
        
        # State trackers
        self.elo_dict: Dict[str, float] = {}
        self.match_history: Dict[str, list] = {}  # Tracks 1 (win) or 0 (loss) for each team
        self.h2h_history: Dict[str, list] = {}    # Tracks wins for "teamA_teamB" (sorted alphabetically)

    def _get_elo(self, team: str) -> float:
        if team not in self.elo_dict:
            self.elo_dict[team] = self.base_elo
        return self.elo_dict[team]

    def _expected_score(self, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))

    def _update_elo(self, team1: str, team2: str, team1_won: bool):
        r1 = self._get_elo(team1)
        r2 = self._get_elo(team2)
        
        e1 = self._expected_score(r1, r2)
        e2 = self._expected_score(r2, r1)
        
        s1 = 1.0 if team1_won else 0.0
        s2 = 0.0 if team1_won else 1.0
        
        self.elo_dict[team1] = r1 + self.k_factor * (s1 - e1)
        self.elo_dict[team2] = r2 + self.k_factor * (s2 - e2)

    def _get_rolling_winrate(self, team: str, window: int) -> float:
        history = self.match_history.get(team, [])
        if len(history) == 0:
            return 0.5  # default unknown
        recent = history[-window:]
        return sum(recent) / len(recent)

    def _update_history(self, team1: str, team2: str, team1_won: bool):
        if team1 not in self.match_history:
            self.match_history[team1] = []
        if team2 not in self.match_history:
            self.match_history[team2] = []
            
        self.match_history[team1].append(1 if team1_won else 0)
        self.match_history[team2].append(0 if team1_won else 1)
        
        # H2H tracking (sort to ensure consistent key regardless of who is team1)
        teams = sorted([team1, team2])
        h2h_key = f"{teams[0]}_vs_{teams[1]}"
        
        if h2h_key not in self.h2h_history:
            self.h2h_history[h2h_key] = []
            
        # Store 1 if teams[0] won, else 0
        teams0_won = team1_won if team1 == teams[0] else not team1_won
        self.h2h_history[h2h_key].append(1 if teams0_won else 0)

    def _get_h2h_winrate(self, query_team: str, other_team: str) -> float:
        teams = sorted([query_team, other_team])
        h2h_key = f"{teams[0]}_vs_{teams[1]}"
        history = self.h2h_history.get(h2h_key, [])
        
        if len(history) == 0:
            return 0.5
            
        wins_for_teams0 = sum(history)
        if query_team == teams[0]:
            return wins_for_teams0 / len(history)
        else:
            return (len(history) - wins_for_teams0) / len(history)

    def compute_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a chronologically sorted DataFrame of matches and computes
        pre-match features (ELO, win-rates) for every row, updating state AFTER the row.
        """
        # Ensure it's sorted
        if not pd.to_datetime(df['match_date'], errors='coerce').is_monotonic_increasing:
            print("WARNING: DataFrame is not strictly chronologically sorted. Calculating ELO may have leakage!")
            
        features = []
        
        for idx, row in df.iterrows():
            t1 = row['team1']
            t2 = row['team2']
            winner = row.get('winner')
            
            # 1. Extract PRE-MATCH features
            row_feats = {
                'team1_elo': self._get_elo(t1),
                'team2_elo': self._get_elo(t2),
                'elo_diff': self._get_elo(t1) - self._get_elo(t2),
                
                'team1_winrate_5': self._get_rolling_winrate(t1, 5),
                'team2_winrate_5': self._get_rolling_winrate(t2, 5),
                'team1_winrate_10': self._get_rolling_winrate(t1, 10),
                'team2_winrate_10': self._get_rolling_winrate(t2, 10),
                
                'team1_h2h_winrate': self._get_h2h_winrate(t1, t2)
            }
            features.append(row_feats)
            
            # 2. Update state POST-MATCH (if there is a clear winner)
            if winner and (winner == t1 or winner == t2):
                t1_won = (winner == t1)
                self._update_elo(t1, t2, t1_won)
                self._update_history(t1, t2, t1_won)
                
        feat_df = pd.DataFrame(features, index=df.index)
        return pd.concat([df, feat_df], axis=1)

if __name__ == "__main__":
    # Quick structural test
    df_test = pd.DataFrame({
        'match_date': ['2020-01-01', '2020-01-02', '2020-01-03'],
        'team1': ['India', 'India', 'Australia'],
        'team2': ['Australia', 'England', 'England'],
        'winner': ['India', 'England', 'Australia']
    })
    
    agent = SportsMathAgent()
    out = agent.compute_all_features(df_test)
    print(out[['match_date', 'team1', 'team2', 'winner', 'team1_elo', 'team2_elo', 'elo_diff', 'team1_winrate_5']])
