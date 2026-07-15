import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DB_PATH = os.path.join(BASE_DIR, "data", "datasets", "cricsheet", "cricsheet_datalake.db")

class PlayerStatsAgent:
    """
    Analyzes historical player performance to extract Player Intelligence.
    Calculates rolling batting form, bowling economy, and strike rates.
    """
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)

    def get_player_recent_form(self, player_name, innings_count=5):
        """Fetch the last N innings for a specific player."""
        query = f"""
            SELECT runs_scored, balls_faced, wickets, runs_conceded, balls_bowled
            FROM player_match_stats
            WHERE player_name = ?
            ORDER BY match_date DESC
            LIMIT {innings_count}
        """
        df = pd.read_sql_query(query, self.conn, params=(player_name,))
        if df.empty:
            return None
        
        runs = df["runs_scored"].sum()
        balls = df["balls_faced"].sum()
        wickets = df["wickets"].sum()
        runs_c = df["runs_conceded"].sum()
        balls_b = df["balls_bowled"].sum()
        
        strike_rate = (runs / balls * 100) if balls > 0 else 0
        economy = (runs_c / (balls_b / 6)) if balls_b > 0 else 0
        
        return {
            "runs_scored": runs,
            "strike_rate": strike_rate,
            "wickets": wickets,
            "economy": economy
        }

    def aggregate_team_power(self, playing_xi):
        """
        Takes a list of 11 player names (Playing XI) and calculates 
        the aggregated Batting and Bowling Power of the team.
        """
        total_runs = 0
        total_wickets = 0
        valid_batsmen = 0
        valid_bowlers = 0
        
        for player in playing_xi:
            form = self.get_player_recent_form(player, innings_count=10)
            if form:
                total_runs += form["runs_scored"]
                if form["runs_scored"] > 50:
                    valid_batsmen += 1
                
                total_wickets += form["wickets"]
                if form["wickets"] > 2:
                    valid_bowlers += 1
                    
        return {
            "team_batting_power": total_runs,
            "team_bowling_power": total_wickets,
            "form_players_count": valid_batsmen + valid_bowlers
        }
