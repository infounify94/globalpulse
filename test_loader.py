import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()

from etl.parsers.cricsheet_parser import CricsheetParser
from etl.loaders.postgres_loader import PostgresLoader
from core.memory.schema import get_engine

url = os.environ.get("SUPABASE_DB_URL")
engine = get_engine(url)

# Make a fake match file
fake_data = {
    "info": {
        "match_type": "T20",
        "dates": ["2016-09-06"],
        "venue": "R Premadasa Stadium",
        "teams": ["Australia", "Sri Lanka"],
        "toss": {"winner": "Sri Lanka", "decision": "bat"},
        "outcome": {"winner": "Australia", "by": {"runs": 85}}
    },
    "innings": [
        {
            "team": "Australia",
            "overs": [
                {
                    "over": 0,
                    "deliveries": [
                        {
                            "batter": "DA Warner",
                            "bowler": "SL Malinga",
                            "non_striker": "AJ Finch",
                            "runs": {"batter": 0, "extras": 0, "total": 0}
                        }
                    ]
                }
            ]
        }
    ]
}

filepath = "fake_980915.json"
with open(filepath, "w") as f:
    json.dump(fake_data, f)

parser = CricsheetParser()
event, metadata, teams, venue, innings, deliveries, players = parser.parse(filepath)

loader = PostgresLoader(engine)
try:
    print(f"Players extracted: {[p.id for p in players]}")
    loader.load_match(event, metadata, teams, venue, innings, deliveries, players)
    print("SUCCESS!")
except Exception as e:
    print(f"ERROR: {e}")
