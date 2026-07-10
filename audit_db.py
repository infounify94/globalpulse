from supabase import create_client
url = 'https://qzmojqtejmdowkdctlxm.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6bW9qcXRlam1kb3drZGN0bHhtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzQyODgwNCwiZXhwIjoyMDk5MDA0ODA0fQ.SBOA0gNLvMLNJGW13fSS8uj8tb7KLvrbbUBDfSnNYUM'
sb = create_client(url, key)

# 1. Check champion model
champ = sb.table('model_registry').select('*').eq('is_champion', True).execute()
print(f'CHAMPIONS: {len(champ.data)}')
if champ.data:
    c = champ.data[0]
    print(f'  Champion ID: {c.get("id")}')
    print(f'  Storage path: {c.get("storage_path")}')
    print(f'  Algorithm: {c.get("algorithm")}')
    print(f'  Performance: {c.get("performance_metrics")}')

# 2. Check dashboard_summary content
ds = sb.table('dashboard_summary').select('*').limit(1).execute()
print(f'DASHBOARD_SUMMARY:')
if ds.data:
    print(f'  {ds.data[0]}')

# 3. Check shadow_predictions
sp = sb.table('shadow_predictions').select('*').limit(5).execute()
print(f'SHADOW_PREDICTIONS: {len(sp.data)} rows')

# 4. Check prediction_store recent
ps = sb.table('prediction_store').select('*').order('prediction_timestamp', desc=True).limit(3).execute()
print(f'PREDICTION_STORE recent:')
for p in ps.data:
    print(f'  match_id={p.get("match_id")}, status={p.get("prediction_status")}, ts={p.get("prediction_timestamp")}')

# 5. Check system_health
sh = sb.table('system_health').select('*').limit(1).execute()
print(f'SYSTEM_HEALTH: {sh.data}')

# 6. Check storage buckets
try:
    buckets = sb.storage.list_buckets()
    print(f'STORAGE BUCKETS: {[b.name for b in buckets]}')
    files = sb.storage.from_('models').list()
    print(f'MODELS BUCKET FILES (root): {[f["name"] for f in files[:10]]}')
except Exception as e:
    print(f'STORAGE ERROR: {e}')

# 7. Check training_runs 
tr = sb.table('training_runs').select('*').order('timestamp', desc=True).limit(3).execute()
print(f'TRAINING_RUNS recent:')
for r in tr.data:
    print(f'  {r}')

# 8. Check events sample
ev = sb.table('events').select('id, event_type, date, outcome').order('date', desc=True).limit(3).execute()
print(f'EVENTS recent:')
for e in ev.data:
    print(f'  {e}')
