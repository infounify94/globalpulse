import os
import requests
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, "data", "datasets", "geomagnetic")
DB_PATH = os.path.join(BASE_DIR, "data", "datasets", "cricsheet", "cricsheet_datalake.db")

def init_kp_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS geomagnetic_kp (
        timestamp TEXT PRIMARY KEY,
        kp_index REAL
    )
    ''')
    conn.commit()

def fetch_historical_kp(conn):
    os.makedirs(DATA_DIR, exist_ok=True)
    print("Fetching historical Kp index from GFZ Potsdam (Official Source)...")
    
    # We fetch from 2000-01-01 up to the current day.
    # The Kp index is provided in 3-hour intervals.
    start_date = "2000-01-01T00:00:00Z"
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    url = f"https://kp.gfz-potsdam.de/app/json/?start={start_date}&end={end_date}&index=Kp"
    
    response = requests.get(url)
    response.raise_for_status()
    
    data = response.json()
    datetimes = data.get('datetime', [])
    kp_values = data.get('Kp', [])
    
    if len(datetimes) != len(kp_values):
        raise ValueError("Mismatched arrays from GFZ API")
        
    print(f"Retrieved {len(kp_values)} 3-hour Kp index records. Inserting into Data Lake...")
    
    records = []
    for dt, kp in zip(datetimes, kp_values):
        records.append((dt, kp))
        
    cursor = conn.cursor()
    cursor.executemany('''
    INSERT OR REPLACE INTO geomagnetic_kp (timestamp, kp_index)
    VALUES (?, ?)
    ''', records)
    
    conn.commit()
    print("Geomagnetic Kp data successfully archived.")

def main():
    conn = sqlite3.connect(DB_PATH)
    init_kp_table(conn)
    
    try:
        fetch_historical_kp(conn)
    except Exception as e:
        print(f"Error fetching Kp Data: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
