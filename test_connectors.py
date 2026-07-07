import os, sys

# Load .env manually
for line in open('.env'):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

print("=== Testing CricAPI (Current Matches) ===")
from core.etl.connectors.live_connector import ScheduleConnector, ScoreConnector
sched = ScheduleConnector()
matches = sched.fetch_upcoming_matches()
print(f"Current matches found: {len(matches)}")
if matches:
    m = matches[0]
    print(f"  Sample: {m.get('team_a')} vs {m.get('team_b')} | {m.get('date')} | source={m.get('source')}")

print()
print("=== Testing CricAPI (Live Scores) ===")
scorer = ScoreConnector()
scores = scorer.fetch_live_scores()
print(f"Live score feeds: {len(scores)}")
if scores:
    s = scores[0]
    print(f"  Sample: {s.get('title')} | {s.get('status')}")

print()
print("=== Testing OpenWeatherMap ===")
from core.etl.connectors.weather_connector import WeatherConnector
from datetime import datetime, timedelta
wc = WeatherConnector()
future_date = datetime.utcnow() + timedelta(days=2)
w = wc.fetch_weather("lords", future_date)
print(f"Weather at Lords in 2 days:")
print(f"  Temp={w.get('env_temperature_c', 'N/A')}C  Wind={w.get('env_windspeed_kmh', 'N/A')}km/h  Rain={w.get('env_precipitation_mm', 'N/A')}mm")

print()
print("=== Testing historical weather (Open-Meteo) ===")
from datetime import timedelta
hist_date = datetime.utcnow() - timedelta(days=30)
wh = wc.fetch_weather("mcg", hist_date)
print(f"MCG 30 days ago: Temp={wh.get('env_temperature_c', 'N/A')}C  Rain={wh.get('env_precipitation_mm', 'N/A')}mm")

print()
print("All connector tests complete.")
