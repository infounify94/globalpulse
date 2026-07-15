import os
import sqlite3
from core.agents.signal_agents.geomagnetic_agent import GeomagneticAgent

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "datasets", "cricsheet", "cricsheet_datalake.db")

def test_geomagnetic_features():
    print("Testing Geomagnetic Agent Feature Extraction...\n")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Let's pick 3 random historical matches from different eras
    cursor.execute('''
        SELECT match_id, match_date, team1, team2, format 
        FROM matches 
        WHERE match_date IS NOT NULL
        ORDER BY RANDOM() LIMIT 5
    ''')
    matches = cursor.fetchall()
    conn.close()
    
    agent = GeomagneticAgent()
    
    for m in matches:
        match_id, match_date, team1, team2, match_format = m
        print(f"Match: {team1} vs {team2} ({match_format}) on {match_date}")
        
        # Generate the features strictly using data from BEFORE match_date
        features = agent.compute_features({}, match_date)
        print(f"  -> Generated Features (Prior 24h Kp Index):")
        print(f"     Max Kp: {features['kp_24h_max']} (High values indicate solar storms)")
        print(f"     Avg Kp: {features['kp_24h_avg']}")
        print("-" * 50)
        
    agent.close()

if __name__ == "__main__":
    test_geomagnetic_features()
