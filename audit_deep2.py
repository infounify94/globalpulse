"""Deep schema and data audit."""
import sqlite3, json
from datetime import datetime, timezone

db = sqlite3.connect('globalpulse_dev.db')
db.row_factory = sqlite3.Row
c = db.cursor()

print('=== PREDICTION_STORE sample rows ===')
c.execute('SELECT * FROM prediction_store LIMIT 3')
rows = [dict(r) for r in c.fetchall()]
for r in rows:
    print(json.dumps(r, default=str)[:400])

print()
print('=== EVENTS sample ===')
c.execute('SELECT * FROM events LIMIT 3')
rows = [dict(r) for r in c.fetchall()]
for r in rows:
    print(json.dumps(r, default=str)[:300])

print()
print('=== CRICKET_MATCH_METADATA sample ===')
c.execute('SELECT * FROM cricket_match_metadata LIMIT 3')
rows = [dict(r) for r in c.fetchall()]
for r in rows:
    print(json.dumps(r, default=str)[:300])

print()
print('=== MODEL_REGISTRY champion ===')
c.execute('SELECT * FROM model_registry WHERE is_champion=1 LIMIT 1')
row = c.fetchone()
if row:
    r = dict(row)
    perf = json.loads(r.get('performance_metrics') or '{}')
    print('model_version:', r.get('model_version'))
    print('algorithm:', r.get('algorithm'))
    print('training_date:', r.get('training_date'))
    print('performance_metrics:', json.dumps(perf)[:500])
    print('checksum:', r.get('checksum'))
else:
    print('NO CHAMPION FOUND')

print()
c.execute('SELECT COUNT(*) FROM model_registry WHERE is_champion=1')
print('Champion count:', c.fetchone()[0])

print()
c.execute('SELECT COUNT(*) FROM model_registry')
print('Total models:', c.fetchone()[0])

print()
print('=== PREDICTION_STORE stats ===')
c.execute("""SELECT
    COUNT(*) as total,
    SUM(CASE WHEN actual_winner_id IS NOT NULL AND actual_winner_id != 'nan' THEN 1 ELSE 0 END) as has_actual,
    SUM(CASE WHEN actual_winner_id IS NULL OR actual_winner_id = 'nan' THEN 1 ELSE 0 END) as no_actual,
    SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) as correct,
    SUM(CASE WHEN probability IS NULL THEN 1 ELSE 0 END) as null_prob
FROM prediction_store""")
r = dict(c.fetchone())
print(json.dumps(r, default=str))

print()
print('=== MATCH_ID join check ===')
c.execute("""SELECT p.match_id, e.date, e.venue_id, m.team_a_id, m.team_b_id
FROM prediction_store p
LEFT JOIN events e ON p.match_id = e.id
LEFT JOIN cricket_match_metadata m ON p.match_id = m.event_id
LIMIT 5""")
rows = [dict(r) for r in c.fetchall()]
for r in rows:
    print(r)

print()
print('=== SHADOW_PREDICTIONS sample ===')
c.execute('SELECT * FROM shadow_predictions LIMIT 3')
rows = [dict(r) for r in c.fetchall()]
for r in rows:
    print(json.dumps(r, default=str)[:400])

print()
print('=== EXPERIMENT_REGISTRY sample ===')
c.execute('SELECT * FROM experiment_registry ORDER BY start_time DESC LIMIT 3')
rows = [dict(r) for r in c.fetchall()]
for r in rows:
    print(json.dumps(r, default=str)[:400])

print()
print('=== FEATURE_IMPORTANCE table ===')
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feature_importance'")
exists = c.fetchone()
if exists:
    c.execute('SELECT COUNT(*) FROM feature_importance')
    print('feature_importance rows:', c.fetchone()[0])
    c.execute('PRAGMA table_info(feature_importance)')
    cols = [(r[1], r[2]) for r in c.fetchall()]
    print('columns:', cols)
else:
    print('feature_importance TABLE DOES NOT EXIST')

print()
print('=== CHECK dashboard_snapshots ===')
c.execute("SELECT name FROM sqlite_master WHERE name='dashboard_snapshots'")
ds = c.fetchone()
print('dashboard_snapshots exists:', bool(ds))
if ds:
    c.execute('SELECT COUNT(*) FROM dashboard_snapshots')
    print('dashboard_snapshots rows:', c.fetchone()[0])
    c.execute('PRAGMA table_info(dashboard_snapshots)')
    cols = [(r[1], r[2]) for r in c.fetchall()]
    print('columns:', cols)

print()
print('=== CHECK dashboard_summary VIEW ===')
c.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='dashboard_summary'")
dsv = c.fetchone()
print('dashboard_summary view exists:', bool(dsv))

print()
print('=== prediction_store: DUPLICATE IDs ===')
c.execute('SELECT id, COUNT(*) as cnt FROM prediction_store GROUP BY id HAVING cnt > 1 LIMIT 10')
dups = c.fetchall()
print('Duplicate IDs:', len(dups))

print()
print('=== events date range ===')
c.execute('SELECT MIN(date), MAX(date) FROM events')
r = c.fetchone()
print('Events date range:', r[0], 'to', r[1])

db.close()
