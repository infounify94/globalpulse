from supabase import create_client
import json

url = 'https://qzmojqtejmdowkdctlxm.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6bW9qcXRlam1kb3drZGN0bHhtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzQyODgwNCwiZXhwIjoyMDk5MDA0ODA0fQ.SBOA0gNLvMLNJGW13fSS8uj8tb7KLvrbbUBDfSnNYUM'
sb = create_client(url, key)

# Check storage for the champion model file
print("=== STORAGE AUDIT ===")
try:
    # List files in models/2026-07-09/
    files = sb.storage.from_('models').list('models/2026-07-09')
    print(f'Files in models/2026-07-09/: {files}')
except Exception as e:
    print(f'Storage list error: {e}')

# Try to download the champion model
try:
    champ_path = 'models/2026-07-09/sci_audit_7a4d7a44_xgboost.joblib'
    data = sb.storage.from_('models').download(champ_path)
    print(f'Champion model file size: {len(data)} bytes')
    print(f'File content preview: {data[:50]}')
except Exception as e:
    print(f'Champion download error: {e}')

# Check prediction_store - detailed analysis
print("\n=== PREDICTION_STORE ANALYSIS ===")
# Count by status
from datetime import datetime, timedelta

# Get unique statuses
statuses = ['PENDING', 'VERIFIED']
for s in statuses:
    r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', s).execute()
    print(f'  status={s}: count={r.count}')

r2 = sb.table('prediction_store').select('id', count='exact').is_('prediction_status', 'null').execute()
print(f'  status=NULL: count={r2.count}')

# Check if any have is_correct set
ic = sb.table('prediction_store').select('id', count='exact').eq('is_correct', True).execute()
print(f'  is_correct=True: {ic.count}')
ic2 = sb.table('prediction_store').select('id', count='exact').eq('is_correct', False).execute()
print(f'  is_correct=False: {ic2.count}')

# Check sample prediction data
sample = sb.table('prediction_store').select('*').limit(2).execute()
print(f'\nSample prediction rows:')
for p in sample.data:
    print(f'  {json.dumps(p, indent=2, default=str)[:500]}')

# Check dashboard_summary fields vs what frontend expects
print("\n=== DASHBOARD_SUMMARY vs FRONTEND EXPECTATIONS ===")
ds = sb.table('dashboard_summary').select('*').limit(1).execute()
if ds.data:
    keys = list(ds.data[0].keys())
    print(f'DB columns: {keys}')
    print(f'Frontend needs: accuracy, brier_score, roi, total_predictions, average_confidence, champion, previous_champion, drift_percentage, dataset_version, confidence_calibration, live_predictions')
    print(f'Frontend maps:')
    print(f'  accuracy <- latest_accuracy: {ds.data[0].get("latest_accuracy")}')
    print(f'  brier_score <- latest_brier: {ds.data[0].get("latest_brier")}')
    print(f'  roi <- latest_roi: {ds.data[0].get("latest_roi")}')
    print(f'  total_predictions <- live_predictions: {ds.data[0].get("live_predictions")}')
    print(f'  average_confidence <- confidence_calibration: {ds.data[0].get("confidence_calibration")}')
    print(f'  champion: {ds.data[0].get("champion")}')

# Check model_registry columns needed by frontend
print("\n=== MODEL_REGISTRY vs FRONTEND EXPECTATIONS ===")
models = sb.table('model_registry').select('*').eq('is_champion', True).execute()
if models.data:
    m = models.data[0]
    print(f'Frontend needs: accuracy_mean, brier_score, log_loss, auc_roc, is_champion, algorithm, train_start_year, train_end_year, test_end_year')
    print(f'  accuracy_mean: {m.get("accuracy_mean")} [MISSING - stored in performance_metrics={m.get("performance_metrics")}]')
    print(f'  brier_score: {m.get("brier_score")} [MISSING]')
    print(f'  is_champion: {m.get("is_champion")}')
    print(f'  algorithm: {m.get("algorithm")}')

print("\n=== SHADOW_PREDICTIONS TABLE STRUCTURE ===")
# Check if the table has right columns for frontend
try:
    r = sb.table('shadow_predictions').select('*').limit(1).execute()
    print(f'Table exists, 0 rows. Columns would be: predicted_winner, confidence, actual_winner, prediction_timestamp, event_id')
except Exception as e:
    print(f'Error: {e}')

print("\n=== EVENTS TABLE - Check live vs historical ===")
live = sb.table('events').select('id', count='exact').like('id', 'live_%').execute()
hist = sb.table('events').select('id', count='exact').not_.like('id', 'live_%').execute()
print(f'Live events: {live.count}')
print(f'Historical events: {hist.count}')
