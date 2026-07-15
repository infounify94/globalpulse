import os
import sqlite3
from typing import Dict, Any
from datetime import datetime, timedelta
import sys

# Ensure Python can find the core module
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.agents.research_pipeline.feature_generator import FeatureGenerator

DB_PATH = os.path.join(BASE_DIR, "data", "datasets", "cricsheet", "cricsheet_datalake.db")

class GeomagneticAgent(FeatureGenerator):
    """
    Layer 1 Agent: Geomagnetic Activity (Kp Index)
    Generates features based on planetary geomagnetic disturbances.
    """
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        
    def compute_features(self, match_metadata: Dict[str, Any], match_date_str: str) -> Dict[str, float]:
        """
        Compute Geomagnetic features for a match strictly using knowledge BEFORE the match date.
        We look at the 24 hours preceding the match date.
        """
        try:
            # Parse the match date. CricSheet dates are usually YYYY-MM-DD.
            match_date = datetime.strptime(match_date_str, "%Y-%m-%d")
        except ValueError:
            return {"kp_24h_avg": 0.0, "kp_24h_max": 0.0} # Fallback for malformed dates
            
        # The period of interest: 24 hours before the day of the match
        # (This ensures no data leakage, as we don't even look at the match day itself).
        period_end = match_date.strftime("%Y-%m-%dT00:00:00Z")
        period_start = (match_date - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT kp_index FROM geomagnetic_kp 
            WHERE timestamp >= ? AND timestamp < ?
        ''', (period_start, period_end))
        
        records = cursor.fetchall()
        
        if not records:
            # Missing data
            return {"kp_24h_avg": 0.0, "kp_24h_max": 0.0}
            
        kp_values = [r[0] for r in records]
        
        return {
            "kp_24h_avg": round(sum(kp_values) / len(kp_values), 3),
            "kp_24h_max": round(max(kp_values), 3)
        }
        
    def close(self):
        self.conn.close()
