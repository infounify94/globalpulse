"""Full Supabase Forensic Audit - Unicode safe."""
import os, json, sys
from datetime import datetime, timezone

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ['SUPABASE_URL'] = 'https://qzmojqtejmdowkdctlxm.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6bW9qcXRlam1kb3drZGN0bHhtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzQyODgwNCwiZXhwIjoyMDk5MDA0ODA0fQ.SBOA0gNLvMLNJGW13fSS8uj8tb7KLvrbbUBDfSnNYUM'

from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
now_iso = datetime.now(timezone.utc).isoformat()

issues = []

def check(label, condition, severity='CRITICAL'):
    status = 'OK' if condition else severity
    marker = '[OK]' if condition else ('[!!]' if severity == 'CRITICAL' else '[W]')
    print(f"  {marker} {label}")
    if not condition:
        issues.append(f"[{severity}] {label}")

print("=" * 60)
print("PHASE 5 — MATCH STATUS VALIDATION")
print("=" * 60)

# VERIFIED with no actual_winner
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'VERIFIED').is_('actual_winner_id', 'null').execute()
verified_no_winner = r.count
print(f"  VERIFIED with null actual_winner: {verified_no_winner}")
check("VERIFIED rows always have actual_winner", verified_no_winner == 0, 'CRITICAL')

print()
print("=" * 60)
print("PHASE 6 — MODEL_REGISTRY AUDIT")
print("=" * 60)

r = sb.table('model_registry').select('*').execute()
models = r.data or []
print(f"  Total models: {len(models)}")

champions = [m for m in models if m.get('is_champion')]
print(f"  Champion count (must be 1): {len(champions)}")
check("Exactly 1 champion", len(champions) == 1, 'CRITICAL')

if champions:
    champ = champions[0]
    print(f"  Champion: model_version={champ.get('model_version')}")
    print(f"  Champion: algorithm={champ.get('algorithm')}")
    print(f"  Champion: accuracy_mean={champ.get('accuracy_mean')}")
    print(f"  Champion: auc_roc={champ.get('auc_roc')}")
    print(f"  Champion: brier_score={champ.get('brier_score')}")
    print(f"  Champion: log_loss={champ.get('log_loss')}")
    print(f"  Champion: training_date={champ.get('training_date')}")
    print(f"  Champion: checksum={champ.get('checksum')}")
    check("Champion has model_version", bool(champ.get('model_version')), 'CRITICAL')
    check("Champion has accuracy_mean", champ.get('accuracy_mean') is not None, 'CRITICAL')
    check("Champion has auc_roc", champ.get('auc_roc') is not None, 'CRITICAL')
    check("Champion has training_date", bool(champ.get('training_date')), 'WARNING')
    check("Champion has checksum", bool(champ.get('checksum')), 'WARNING')

print()
print("=" * 60)
print("PHASE 7 — METRIC CONSISTENCY")
print("=" * 60)

# Compute real accuracy from prediction_store - batch
# Need to pull all verified rows but limit for speed
r_verified = sb.table('prediction_store').select('is_correct').eq('prediction_status', 'VERIFIED').lte('date', now_iso).limit(10000).execute()
verified_rows = r_verified.data or []
if verified_rows:
    correct_count = sum(1 for row in verified_rows if row.get('is_correct') is True or row.get('is_correct') == 1)
    total_verified = len(verified_rows)
    real_accuracy = correct_count / total_verified if total_verified > 0 else 0
    print(f"  Sample ({total_verified} rows): correct={correct_count}, accuracy={real_accuracy:.4f}")
    check("Accuracy is reasonable (>40%)", real_accuracy > 0.4, 'WARNING')

# Check dashboard_snapshots
print()
try:
    r_snap = sb.table('dashboard_snapshots').select('*').order('created_at', desc=True).limit(1).execute()
    if r_snap.data:
        snap = r_snap.data[0]
        print(f"  dashboard_snapshots latest: {json.dumps(snap, default=str)[:600]}")
        check("dashboard_snapshots has data", True, 'WARNING')
    else:
        print("  dashboard_snapshots: EMPTY - metrics will show dashes")
        issues.append("[WARNING] dashboard_snapshots is empty")
except Exception as e:
    print(f"  dashboard_snapshots ERROR: {e}")
    issues.append(f"[CRITICAL] dashboard_snapshots: {e}")

# Check dashboard_summary view
try:
    r_view = sb.table('dashboard_summary').select('*').limit(1).execute()
    if r_view.data:
        view = r_view.data[0]
        print(f"  dashboard_summary view: {json.dumps(view, default=str)[:600]}")
        check("dashboard_summary view has data", True, 'WARNING')
    else:
        print("  dashboard_summary view: EMPTY or missing")
        issues.append("[WARNING] dashboard_summary view empty")
except Exception as e:
    print(f"  dashboard_summary view ERROR: {e}")
    issues.append(f"[CRITICAL] dashboard_summary view: {e}")

print()
print("=" * 60)
print("PHASE 8 — UPCOMING PREDICTIONS")
print("=" * 60)

r = sb.table('prediction_store').select('team_a, team_b, venue, date, probability, confidence, prediction_status').eq('prediction_status', 'PENDING').gt('date', now_iso).order('date').limit(10).execute()
upcoming = r.data or []
print(f"  Upcoming (future PENDING): {len(upcoming)}")
for m in upcoming[:5]:
    print(f"  {m.get('team_a')} vs {m.get('team_b')} @ {m.get('venue')} | {m.get('date')}")

check("Has upcoming predictions", len(upcoming) > 0, 'WARNING')

print()
print("=" * 60)
print("PHASE 9 — RECENT OUTCOMES")
print("=" * 60)

r = sb.table('prediction_store').select('team_a, team_b, predicted_winner_id, actual_winner_id, is_correct, probability, venue, date, verified_time').eq('prediction_status', 'VERIFIED').lte('date', now_iso).order('date', desc=True).limit(5).execute()
outcomes = r.data or []
print(f"  Recent VERIFIED outcomes: {len(outcomes)}")
for o in outcomes[:5]:
    print(f"  {o.get('team_a','?')} vs {o.get('team_b','?')} | pred={o.get('predicted_winner_id')} actual={o.get('actual_winner_id')} correct={o.get('is_correct')} date={o.get('date')}")
check("Has verified outcomes", len(outcomes) > 0, 'WARNING')

print()
print("=" * 60)
print("PHASE 10 — SHADOW_PREDICTIONS")
print("=" * 60)

try:
    r = sb.table('shadow_predictions').select('*').order('date', desc=True).limit(10).execute()
    sp = r.data or []
    print(f"  shadow_predictions rows: {len(sp)}")
    if sp:
        mock_count = sum(1 for s in sp if 'mock' in str(s.get('match_id', '')).lower())
        print(f"  MOCK match_ids detected: {mock_count}")
        check("No mock match IDs in shadow_predictions", mock_count == 0, 'CRITICAL')
        for s in sp[:3]:
            print(f"  match_id={s.get('match_id')} | {s.get('team_a')} vs {s.get('team_b')} | {s.get('date')} | prob={s.get('probability')}")
except Exception as e:
    print(f"  shadow_predictions ERROR: {e}")
    issues.append(f"[CRITICAL] shadow_predictions: {e}")

print()
print("=" * 60)
print("PHASE 11 — EXPERIMENT_REGISTRY")
print("=" * 60)

try:
    r = sb.table('experiment_registry').select('*').order('start_time', desc=True).limit(5).execute()
    exps = r.data or []
    print(f"  experiment_registry rows: {len(exps)}")
    for e in exps[:3]:
        metrics = e.get('metrics_summary') or {}
        print(f"  ID={e.get('id')[:20]} status={'COMPLETED' if e.get('end_time') else 'RUNNING'} ds={e.get('dataset_version')}")
    check("Has experiments", len(exps) > 0, 'WARNING')
except Exception as e:
    print(f"  experiment_registry ERROR: {e}")
    issues.append(f"[CRITICAL] experiment_registry: {e}")

print()
print("=" * 60)
print("PHASE 12 — FEATURE_IMPORTANCE")
print("=" * 60)

try:
    r = sb.table('feature_importance').select('*').order('importance', desc=True).limit(20).execute()
    feats = r.data or []
    print(f"  feature_importance rows: {len(feats)}")
    if feats:
        cols = list(feats[0].keys()) if feats else []
        print(f"  columns: {cols}")
        for f in feats[:5]:
            print(f"  {f.get('feature_name')}: importance={f.get('importance')}, shap={f.get('shap_mean')}, model={f.get('model_version')}")
    check("Has feature importance data", len(feats) >= 10, 'CRITICAL')
    check("Has 20 features", len(feats) >= 20, 'WARNING')
except Exception as e:
    print(f"  feature_importance ERROR: {e}")
    issues.append(f"[CRITICAL] feature_importance: {e}")

print()
print("=" * 60)
print("PHASE 14 — DATE INTEGRITY CHECK")
print("=" * 60)

# Check for bad dates
r = sb.table('prediction_store').select('date').lte('date', '2000-01-01').limit(5).execute()
old_dates = r.data or []
print(f"  Rows with date before 2000: {len(old_dates)}")

r = sb.table('prediction_store').select('date').gte('date', '2030-01-01').limit(5).execute()
far_future = r.data or []
print(f"  Rows with date after 2030: {len(far_future)}")
if far_future:
    for f in far_future[:3]:
        print(f"    date={f.get('date')}")

print()
print("=" * 60)
print("PHASE 17 — PRODUCTION VALIDATION SUMMARY")
print("=" * 60)
print(f"\n  Total Issues Found: {len(issues)}")
for i, issue in enumerate(issues, 1):
    print(f"  {i}. {issue}")

if not issues:
    print("  ALL CHECKS PASSED")

print("\nDone.")
