import os
import glob
import json
import sqlite3
from datetime import datetime
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, "data", "datasets", "cricsheet")
RAW_JSON_DIR = os.path.join(DATA_DIR, "raw_json")
DB_PATH = os.path.join(DATA_DIR, "cricsheet_datalake.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # We use SQLite as the immediate local data lake for the MVP.
    # We can easily export this to Parquet via DuckDB later.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        match_id TEXT PRIMARY KEY,
        format TEXT,
        match_date TEXT,
        venue TEXT,
        city TEXT,
        team1 TEXT,
        team2 TEXT,
        toss_winner TEXT,
        toss_decision TEXT,
        winner TEXT,
        win_margin TEXT,
        player_of_match TEXT
    )
    ''')
    conn.commit()
    return conn

def parse_match_data(filepath, format_type):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    info = data.get('info', {})
    
    # Extract dates. We take the first date as the match date.
    dates = info.get('dates', [])
    match_date = dates[0] if dates else None
    
    teams = info.get('teams', [])
    team1 = teams[0] if len(teams) > 0 else None
    team2 = teams[1] if len(teams) > 1 else None
    
    toss = info.get('toss', {})
    toss_winner = toss.get('winner')
    toss_decision = toss.get('decision')
    
    outcome = info.get('outcome', {})
    winner = outcome.get('winner')
    
    # Extract margin if available
    win_margin = None
    by = outcome.get('by', {})
    if 'runs' in by:
        win_margin = f"{by['runs']} runs"
    elif 'wickets' in by:
        win_margin = f"{by['wickets']} wickets"
        
    pom = info.get('player_of_match', [])
    player_of_match = pom[0] if pom else None
    
    match_id = os.path.basename(filepath).split('.')[0]
    
    return (
        match_id,
        format_type,
        match_date,
        info.get('venue'),
        info.get('city'),
        team1,
        team2,
        toss_winner,
        toss_decision,
        winner,
        win_margin,
        player_of_match
    )

def main():
    print(f"Initializing Data Lake at {DB_PATH}")
    conn = init_db()
    cursor = conn.cursor()
    
    folders = ['t20s', 'odis', 'tests', 'ipl']
    total_parsed = 0
    start_time = time.time()
    
    for folder in folders:
        folder_path = os.path.join(RAW_JSON_DIR, folder)
        if not os.path.exists(folder_path):
            continue
            
        json_files = glob.glob(os.path.join(folder_path, '*.json'))
        print(f"Parsing {len(json_files)} {folder} matches...")
        
        batch = []
        for file in json_files:
            try:
                record = parse_match_data(file, folder)
                batch.append(record)
            except Exception as e:
                print(f"Error parsing {file}: {e}")
                
            if len(batch) >= 1000:
                cursor.executemany('''
                INSERT OR REPLACE INTO matches 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', batch)
                conn.commit()
                batch = []
                
        # Insert remaining
        if batch:
            cursor.executemany('''
            INSERT OR REPLACE INTO matches 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch)
            conn.commit()
            
        total_parsed += len(json_files)
        
    conn.close()
    duration = time.time() - start_time
    print(f"\nSuccessfully parsed {total_parsed} matches into SQLite in {duration:.2f} seconds.")
    print("This SQLite database acts as the single source of truth for the Research Agent pipeline.")

if __name__ == "__main__":
    main()
