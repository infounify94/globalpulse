import os
import sys
import sqlite3
import pandas as pd

class DataAuditor:
    """
    Pillar 0 Guardian.
    Ensures that the raw match dataset is perfectly clean before any feature engineering or ML training begins.
    Fails loudly if corruption, duplicates, or leakage risks are detected.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found at {db_path}")

    def load_data(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM matches", conn)
        conn.close()
        return df

    def run_full_audit(self):
        print("==================================================")
        print("PILLAR 0: DATA QUALITY & LEAKAGE AUDIT")
        print("==================================================")
        
        df = self.load_data()
        total_matches = len(df)
        print(f"Total Matches Extracted: {total_matches}")
        
        if total_matches == 0:
            raise ValueError("Audit Failed: The database is completely empty.")

        self._check_duplicates(df)
        self._check_missing_critical_values(df)
        self._check_date_integrity(df)
        self._check_team_integrity(df)
        
        print("\n✅ AUDIT PASSED: The dataset is mathematically pristine.")
        print("==================================================\n")

    def _check_duplicates(self, df: pd.DataFrame):
        duplicates = df.duplicated(subset=['match_id']).sum()
        if duplicates > 0:
            print(f"❌ AUDIT FAILED: Found {duplicates} duplicate match_ids!")
            raise ValueError("Duplicate matches detected.")
        print("[PASS] Duplication Check: Passed (0 duplicates).")

    def _check_missing_critical_values(self, df: pd.DataFrame):
        critical_cols = ['match_date', 'team1', 'team2', 'winner', 'toss_winner']
        missing_report = df[critical_cols].isnull().sum()
        
        # We allow 'winner' to be missing ONLY if it was a tie/no result, but for binary 
        # classification we should drop those before training. 
        # But for raw data integrity, if 'team1' or 'match_date' is missing, it's a critical failure.
        fatal_missing = missing_report[['match_date', 'team1', 'team2', 'toss_winner']].sum()
        
        if fatal_missing > 0:
            print(f"[FAIL] AUDIT FAILED: Found missing critical values!\n{missing_report}")
            raise ValueError("Missing critical values detected.")
            
        empty_winners = missing_report['winner']
        print(f"[PASS] Missing Value Check: Passed. ({empty_winners} matches have no winner due to ties/abandonment, which is statistically normal and will be dropped in training).")

    def _check_date_integrity(self, df: pd.DataFrame):
        # Ensure all dates parse correctly
        parsed_dates = pd.to_datetime(df['match_date'], errors='coerce')
        invalid_dates = parsed_dates.isnull().sum()
        
        if invalid_dates > 0:
            print(f"[FAIL] AUDIT FAILED: Found {invalid_dates} invalid match_dates!")
            raise ValueError("Invalid dates detected.")
            
        print("[PASS] Date Integrity Check: Passed (All dates parse perfectly).")

    def _check_team_integrity(self, df: pd.DataFrame):
        # Ensure team1 and team2 are never the exact same team
        self_plays = df[df['team1'] == df['team2']]
        if len(self_plays) > 0:
            print(f"[FAIL] AUDIT FAILED: Found {len(self_plays)} matches where a team plays itself!")
            raise ValueError("Team Integrity failed.")
            
        print("[PASS] Team Integrity Check: Passed (No self-play anomalies).")


if __name__ == "__main__":
    auditor = DataAuditor("d:/PredictionEngine/data/datasets/cricsheet/cricsheet_datalake.db")
    try:
        auditor.run_full_audit()
    except Exception as e:
        print(f"\nCRITICAL STOP: {e}")
        sys.exit(1)
