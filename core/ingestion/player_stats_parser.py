import os
import json
import glob
import sqlite3
import pandas as pd
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(BASE_DIR, "data", "datasets", "cricsheet", "cricsheet_datalake.db")
RAW_JSON_DIR = os.path.join(BASE_DIR, "data", "datasets", "cricsheet", "raw_json")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_match_stats (
            match_id TEXT,
            match_date TEXT,
            format TEXT,
            player_name TEXT,
            team TEXT,
            runs_scored INTEGER DEFAULT 0,
            balls_faced INTEGER DEFAULT 0,
            fours INTEGER DEFAULT 0,
            sixes INTEGER DEFAULT 0,
            wickets INTEGER DEFAULT 0,
            runs_conceded INTEGER DEFAULT 0,
            balls_bowled INTEGER DEFAULT 0,
            PRIMARY KEY (match_id, player_name)
        )
    """)
    conn.commit()
    return conn

def parse_all_files():
    conn = init_db()
    cursor = conn.cursor()
    
    # Check if we already parsed
    count = cursor.execute("SELECT COUNT(*) FROM player_match_stats").fetchone()[0]
    if count > 0:
        print(f"player_match_stats already populated with {count} records. Dropping and rebuilding...")
        cursor.execute("DROP TABLE player_match_stats")
        conn.commit()
        init_db()

    files = glob.glob(os.path.join(RAW_JSON_DIR, "*", "*.json"))
    print(f"Found {len(files)} JSON files to parse.")

    records_to_insert = []
    
    for idx, filepath in enumerate(files):
        if idx > 0 and idx % 1000 == 0:
            print(f"Parsed {idx}/{len(files)} files...")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except:
                continue

        match_id = os.path.splitext(os.path.basename(filepath))[0]
        
        info = data.get("info", {})
        dates = info.get("dates", [])
        match_date = dates[0] if dates else None
        format_type = info.get("match_type", "unknown")
        
        # Player stats dictionary: player_name -> stats
        stats = defaultdict(lambda: {
            "team": "Unknown",
            "runs_scored": 0, "balls_faced": 0, "fours": 0, "sixes": 0,
            "wickets": 0, "runs_conceded": 0, "balls_bowled": 0
        })
        
        innings_list = data.get("innings", [])
        for innings in innings_list:
            batting_team = innings.get("team", "Unknown")
            
            for over in innings.get("overs", []):
                for delivery in over.get("deliveries", []):
                    batter = delivery.get("batter")
                    bowler = delivery.get("bowler")
                    
                    runs_batter = delivery.get("runs", {}).get("batter", 0)
                    runs_total = delivery.get("runs", {}).get("total", 0)
                    
                    # Extras that don't count as balls faced by batter: wides, noballs
                    extras = delivery.get("extras", {})
                    is_wide = "wides" in extras
                    
                    # Update Batter
                    if batter:
                        stats[batter]["team"] = batting_team
                        stats[batter]["runs_scored"] += runs_batter
                        if not is_wide:
                            stats[batter]["balls_faced"] += 1
                        if runs_batter == 4:
                            stats[batter]["fours"] += 1
                        elif runs_batter == 6:
                            stats[batter]["sixes"] += 1
                            
                    # Update Bowler
                    if bowler:
                        stats[bowler]["runs_conceded"] += runs_total
                        # wides and noballs don't count as legal balls bowled
                        if "wides" not in extras and "noballs" not in extras:
                            stats[bowler]["balls_bowled"] += 1
                            
                        wickets = delivery.get("wickets", [])
                        for w in wickets:
                            if w.get("kind") not in ["run out", "retired hurt", "obstructing the field"]:
                                stats[bowler]["wickets"] += 1

        for player, s in stats.items():
            records_to_insert.append((
                match_id, match_date, format_type, player, s["team"],
                s["runs_scored"], s["balls_faced"], s["fours"], s["sixes"],
                s["wickets"], s["runs_conceded"], s["balls_bowled"]
            ))
            
        if len(records_to_insert) >= 50000:
            cursor.executemany("""
                INSERT OR IGNORE INTO player_match_stats 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records_to_insert)
            conn.commit()
            records_to_insert = []

    if records_to_insert:
        cursor.executemany("""
            INSERT OR IGNORE INTO player_match_stats 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records_to_insert)
        conn.commit()
        
    print("Creating indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_name ON player_match_stats(player_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_date ON player_match_stats(match_date)")
    conn.commit()
    conn.close()
    print("Player stats parsing complete!")

if __name__ == "__main__":
    parse_all_files()
