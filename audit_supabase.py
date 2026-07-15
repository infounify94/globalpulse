"""
Phase 1-18 Full Supabase Forensic Audit
"""
import os, json
from datetime import datetime, timezone

os.environ['SUPABASE_URL'] = 'https://qzmojqtejmdowkdctlxm.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6bW9qcXRlam1kb3drZGN0bHhtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzQyODgwNCwiZXhwIjoyMDk5MDA0ODA0fQ.SBOA0gNLvMLNJGW13fSS8uj8tb7KLvrbbUBDfSnNYUM'

from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
now_iso = datetime.now(timezone.utc).isoformat()

issues = []

def check(label, condition, severity='CRITICAL'):
    status = 'OK' if condition else severity
    marker = '✅' if condition else ('❌' if severity == 'CRITICAL' else '⚠️')
    print(f"  {marker} {label}")
    if not condition:
        issues.append(f"[{severity}] {label}")

print("=" * 60)
print("PHASE 1 — TABLE INVENTORY (Supabase)")
print("=" * 60)
for table in ['prediction_store', 'model_registry', 'experiment_registry', 'shadow_predictions', 'feature_importance', 'dashboard_snapshots']:
    try:
        r = sb.table(table).select('id', count='exact').limit(1).execute()
        count = r.count if r.count is not None else len(r.data)
        print(f"  {table}: {count} rows")
    except Exception as e:
        print(f"  {table}: ERROR - {e}")

print()
print("=" * 60)
print("PHASE 2 — PREDICTION_STORE SCHEMA")
print("=" * 60)
r = sb.table('prediction_store').select('*').limit(1).execute()
if r.data:
    cols = list(r.data[0].keys())
    print(f"  Columns: {cols}")
    print()
    sample = r.data[0]
    print(f"  Sample: {json.dumps(sample, default=str)[:600]}")

print()
print("=" * 60)
print("PHASE 3 — PREDICTION_STORE INTEGRITY")
print("=" * 60)

# Total count
r = sb.table('prediction_store').select('id', count='exact').execute()
total = r.count
print(f"  Total predictions: {total}")

# PENDING
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'PENDING').execute()
pending = r.count
print(f"  PENDING: {pending}")

# VERIFIED
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'VERIFIED').execute()
verified = r.count
print(f"  VERIFIED: {verified}")

# Future PENDING (upcoming)
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'PENDING').gt('date', now_iso).execute()
upcoming_count = r.count
print(f"  Future PENDING (upcoming): {upcoming_count}")

# PENDING with past dates (stale)
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'PENDING').lt('date', now_iso).execute()
stale_pending = r.count
print(f"  PENDING with past dates (stale): {stale_pending}")
check("No stale PENDING predictions", stale_pending == 0, 'WARNING')

# VERIFIED with future dates
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'VERIFIED').gt('date', now_iso).execute()
future_verified = r.count
print(f"  VERIFIED with future dates: {future_verified}")
check("No future-dated VERIFIED rows", future_verified == 0, 'CRITICAL')

# Null team_a
r = sb.table('prediction_store').select('id', count='exact').is_('team_a', 'null').execute()
null_team_a = r.count
print(f"  NULL team_a: {null_team_a}")
check("No null team_a", null_team_a == 0, 'WARNING')

# Null team_b
r = sb.table('prediction_store').select('id', count='exact').is_('team_b', 'null').execute()
null_team_b = r.count
print(f"  NULL team_b: {null_team_b}")
check("No null team_b", null_team_b == 0, 'WARNING')

# Null venue
r = sb.table('prediction_store').select('id', count='exact').is_('venue', 'null').execute()
null_venue = r.count
print(f"  NULL venue: {null_venue}")
check("No null venue", null_venue == 0, 'WARNING')

# Null date
r = sb.table('prediction_store').select('id', count='exact').is_('date', 'null').execute()
null_date = r.count
print(f"  NULL date: {null_date}")
check("No null date", null_date == 0, 'WARNING')

print()
print("=" * 60)
print("PHASE 5 — MATCH STATUS VALIDATION")
print("=" * 60)

# VERIFIED with no actual_winner
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'VERIFIED').is_('actual_winner_id', 'null').execute()
verified_no_winner = r.count
print(f"  VERIFIED with null actual_winner: {verified_no_winner}")
check("VERIFIED rows always have actual_winner", verified_no_winner == 0, 'CRITICAL')

# Check for correct in PENDING (should be null/None)
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'PENDING').not_.is_('is_correct', 'null').execute()
pending_with_correct = r.count
print(f"  PENDING with is_correct set: {pending_with_correct}")
check("PENDING rows have null is_correct", pending_with_correct == 0, 'WARNING')

print()
print("=" * 60)
print("PHASE 6 — MODEL_REGISTRY AUDIT")
print("=" * 60)

r = sb.table('model_registry').select('*').execute()
models = r.data or []
print(f"  Total models: {len(models)}")

champions = [m for m in models if m.get('is_champion')]
print(f"  Champion count: {len(champions)}")
check("Exactly 1 champion", len(champions) == 1, 'CRITICAL')

if champions:
    champ = champions[0]
    print(f"  Champion version: {champ.get('model_version')}")
    print(f"  Champion algorithm: {champ.get('algorithm')}")
    print(f"  Champion accuracy: {champ.get('accuracy_mean')}")
    print(f"  Champion AUC: {champ.get('auc_roc')}")
    print(f"  Champion training_date: {champ.get('training_date')}")
    print(f"  Champion checksum: {champ.get('checksum')}")
    check("Champion has model_version", bool(champ.get('model_version')), 'CRITICAL')
    check("Champion has accuracy_mean", champ.get('accuracy_mean') is not None, 'CRITICAL')
    check("Champion has auc_roc", champ.get('auc_roc') is not None, 'CRITICAL')
    check("Champion has training_date", bool(champ.get('training_date')), 'WARNING')

print()
print("=" * 60)
print("PHASE 7 — METRIC CONSISTENCY")
print("=" * 60)

# Compute real accuracy from prediction_store
r_verified = sb.table('prediction_store').select('is_correct').eq('prediction_status', 'VERIFIED').lte('date', now_iso).execute()
verified_rows = r_verified.data or []
if verified_rows:
    correct_count = sum(1 for row in verified_rows if row.get('is_correct') is True or row.get('is_correct') == 1)
    total_verified = len(verified_rows)
    real_accuracy = correct_count / total_verified if total_verified > 0 else 0
    print(f"  Computed accuracy: {correct_count}/{total_verified} = {real_accuracy:.4f}")
    check("Accuracy is reasonable (>40%)", real_accuracy > 0.4, 'WARNING')
else:
    print("  No verified rows for accuracy computation")

# Check dashboard_snapshots
try:
    r_snap = sb.table('dashboard_snapshots').select('*').order('created_at', desc=True).limit(1).execute()
    if r_snap.data:
        snap = r_snap.data[0]
        print(f"  dashboard_snapshots latest: {json.dumps(snap, default=str)[:500]}")
    else:
        print("  dashboard_snapshots: EMPTY")
        issues.append("[WARNING] dashboard_snapshots is empty — metrics dashboard will show —")
except Exception as e:
    print(f"  dashboard_snapshots ERROR: {e}")
    issues.append(f"[CRITICAL] dashboard_snapshots table missing: {e}")

# Check dashboard_summary view
try:
    r_view = sb.table('dashboard_summary').select('*').limit(1).execute()
    if r_view.data:
        view = r_view.data[0]
        print(f"  dashboard_summary view: {json.dumps(view, default=str)[:500]}")
    else:
        print("  dashboard_summary view: EMPTY")
        issues.append("[WARNING] dashboard_summary view returns no data")
except Exception as e:
    print(f"  dashboard_summary view ERROR: {e}")
    issues.append(f"[CRITICAL] dashboard_summary view missing or broken: {e}")

print()
print("=" * 60)
print("PHASE 8 — UPCOMING PREDICTIONS")
print("=" * 60)

r = sb.table('prediction_store').select('team_a, team_b, venue, date, probability, confidence, prediction_status').eq('prediction_status', 'PENDING').gt('date', now_iso).order('date').limit(5).execute()
upcoming = r.data or []
print(f"  Upcoming predictions (future PENDING): {len(upcoming)}")
for m in upcoming[:3]:
    print(f"  {m['team_a']} vs {m['team_b']} @ {m.get('venue','?')} | {m['date']} | prob={m.get('probability')}")

check("Has upcoming predictions", len(upcoming) > 0, 'WARNING')

print()
print("=" * 60)
print("PHASE 9 — RECENT OUTCOMES")
print("=" * 60)

r = sb.table('prediction_store').select('team_a, team_b, predicted_winner_id, actual_winner_id, is_correct, probability, venue, date, verified_time').eq('prediction_status', 'VERIFIED').lte('date', now_iso).order('date', desc=True).limit(5).execute()
outcomes = r.data or []
print(f"  Recent VERIFIED outcomes: {len(outcomes)}")
for o in outcomes[:3]:
    print(f"  {o.get('team_a','?')} vs {o.get('team_b','?')} | pred={o.get('predicted_winner_id')} actual={o.get('actual_winner_id')} correct={o.get('is_correct')}")

check("Has verified outcomes", len(outcomes) > 0, 'WARNING')

print()
print("=" * 60)
print("PHASE 10 — SHADOW_PREDICTIONS")
print("=" * 60)

try:
    r = sb.table('shadow_predictions').select('*').limit(10).execute()
    sp = r.data or []
    print(f"  shadow_predictions rows: {len(sp)}")
    if sp:
        mock_count = sum(1 for s in sp if 'mock' in str(s.get('match_id', '')).lower())
        print(f"  MOCK match_ids detected: {mock_count}")
        check("No mock match IDs in shadow_predictions", mock_count == 0, 'CRITICAL')
        for s in sp[:2]:
            print(f"  {s.get('team_a')} vs {s.get('team_b')} | {s.get('date')} | prob={s.get('probability')}")
except Exception as e:
    print(f"  shadow_predictions ERROR: {e}")

print()
print("=" * 60)
print("PHASE 11 — EXPERIMENT_REGISTRY")
print("=" * 60)

try:
    r = sb.table('experiment_registry').select('*').order('start_time', desc=True).limit(5).execute()
    exps = r.data or []
    print(f"  experiment_registry rows: {len(exps)}")
    for e in exps[:2]:
        print(f"  ID: {e.get('id')} | status: {'COMPLETED' if e.get('end_time') else 'RUNNING'} | dataset: {e.get('dataset_version')}")
    check("Has experiments", len(exps) > 0, 'WARNING')
except Exception as e:
    print(f"  experiment_registry ERROR: {e}")
    issues.append(f"[CRITICAL] experiment_registry missing: {e}")

print()
print("=" * 60)
print("PHASE 12 — FEATURE_IMPORTANCE")
print("=" * 60)

try:
    r = sb.table('feature_importance').select('*').order('importance', desc=True).limit(5).execute()
    feats = r.data or []
    print(f"  feature_importance rows: {len(feats)}")
    for f in feats[:3]:
        print(f"  {f.get('feature_name')}: importance={f.get('importance')}, shap={f.get('shap_mean')}, model={f.get('model_version')}")
    check("Has feature importance data", len(feats) > 0, 'CRITICAL')
except Exception as e:
    print(f"  feature_importance ERROR: {e}")
    issues.append(f"[CRITICAL] feature_importance missing: {e}")

print()
print("=" * 60)
print("PHASE 17 — PRODUCTION VALIDATION SUMMARY")
print("=" * 60)
print(f"\n  Total Issues Found: {len(issues)}")
for i, issue in enumerate(issues, 1):
    print(f"  {i}. {issue}")

if not issues:
    print("  ✅ All production checks PASSED")

print("\nDone.")
