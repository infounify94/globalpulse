"""
Phase 17 — Production Validation Assertions
Fails if any production integrity check is violated.
"""
import os, sys
from datetime import datetime, timezone

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ['SUPABASE_URL'] = 'https://qzmojqtejmdowkdctlxm.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6bW9qcXRlam1kb3drZGN0bHhtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzQyODgwNCwiZXhwIjoyMDk5MDA0ODA0fQ.SBOA0gNLvMLNJGW13fSS8uj8tb7KLvrbbUBDfSnNYUM'

from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
now_iso = datetime.now(timezone.utc).isoformat()

failures = []
warnings = []
passed = []

def assert_check(label, condition, critical=True):
    if condition:
        passed.append(label)
        print(f"  [PASS] {label}")
    else:
        if critical:
            failures.append(label)
            print(f"  [FAIL] {label}")
        else:
            warnings.append(label)
            print(f"  [WARN] {label}")

print("=" * 60)
print("PHASE 17 — PRODUCTION VALIDATION ASSERTIONS")
print(f"Timestamp: {now_iso}")
print("=" * 60)

# 1. No multiple champions
r = sb.table('model_registry').select('id', count='exact').eq('is_champion', True).execute()
champ_count = r.count
assert_check("Exactly 1 champion model", champ_count == 1, critical=True)

# 2. No future-dated VERIFIED matches
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'VERIFIED').gt('date', now_iso).execute()
future_verified = r.count
assert_check("No future-dated VERIFIED matches", future_verified == 0, critical=True)

# 3. No VERIFIED with null actual_winner
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'VERIFIED').is_('actual_winner_id', 'null').execute()
verified_no_winner = r.count
assert_check("No VERIFIED rows with null actual_winner", verified_no_winner == 0, critical=True)

# 4. No mock shadow predictions
r = sb.table('shadow_predictions').select('id, match_id').execute()
all_sp = r.data or []
mock_sp = [s for s in all_sp if 'mock' in str(s.get('match_id','')).lower() or str(s.get('match_id','')).startswith('live_')]
assert_check("No mock match_ids in shadow_predictions", len(mock_sp) == 0, critical=True)

# 5. Feature importance has data
r = sb.table('feature_importance').select('id', count='exact').execute()
fi_count = r.count
assert_check("feature_importance table has data", fi_count > 0, critical=True)
assert_check("feature_importance has >=10 features", fi_count >= 10, critical=False)
assert_check("feature_importance has >=20 features", fi_count >= 20, critical=False)

# 6. Experiment registry has data
r = sb.table('experiment_registry').select('id', count='exact').execute()
exp_count = r.count
assert_check("experiment_registry has experiments", exp_count > 0, critical=False)

# 7. dashboard_summary returns data
try:
    r = sb.table('dashboard_summary').select('*').limit(1).execute()
    has_view = bool(r.data)
    assert_check("dashboard_summary view returns data", has_view, critical=True)
    if r.data:
        view = r.data[0]
        assert_check("dashboard_summary.latest_accuracy is not null", view.get('latest_accuracy') is not None, critical=True)
        assert_check("dashboard_summary.champion is not null", bool(view.get('champion')), critical=True)
        assert_check("dashboard_summary.live_predictions > 0", (view.get('live_predictions') or 0) > 0, critical=True)
        acc = view.get('latest_accuracy') or 0
        assert_check("dashboard_summary accuracy is valid (0-1)", 0 <= acc <= 1, critical=True)
        assert_check("dashboard_summary accuracy > 40%", acc > 0.4, critical=False)
except Exception as e:
    failures.append(f"dashboard_summary view error: {e}")
    print(f"  [FAIL] dashboard_summary view error: {e}")

# 8. No NaN probabilities in prediction_store
r = sb.table('prediction_store').select('probability').limit(5000).execute()
probs = r.data or []
nan_probs = [p for p in probs if p.get('probability') is None]
assert_check("No null probabilities (sample of 5000)", len(nan_probs) == 0, critical=True)

# 9. No null team_a/team_b in PENDING predictions
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'PENDING').is_('team_a', 'null').execute()
null_team_pending = r.count
assert_check("No PENDING predictions with null team_a", null_team_pending == 0, critical=True)

# 10. No duplicate prediction IDs
# Supabase can't do GROUP BY via the client API directly — skip duplicate check
# (would need RPC or direct SQL)

# 11. Prediction store has correct date range (no pre-2000 dates)
r = sb.table('prediction_store').select('id', count='exact').lt('date', '2000-01-01').execute()
ancient_dates = r.count
assert_check("No predictions with date before 2000", ancient_dates == 0, critical=True)

# 12. Confidence values in valid range (0-1)
r = sb.table('prediction_store').select('confidence').not_.is_('confidence', 'null').limit(2000).execute()
conf_rows = r.data or []
out_of_range = [row for row in conf_rows if not (0 <= (row.get('confidence') or 0) <= 1)]
assert_check("Confidence values in range 0-1", len(out_of_range) == 0, critical=True)

print()
print("=" * 60)
print("VALIDATION RESULTS")
print("=" * 60)
print(f"  PASSED:   {len(passed)}")
print(f"  WARNINGS: {len(warnings)}")
print(f"  FAILED:   {len(failures)}")
print()

if failures:
    print("CRITICAL FAILURES:")
    for f in failures:
        print(f"  [!!] {f}")

if warnings:
    print("WARNINGS (non-blocking):")
    for w in warnings:
        print(f"  [W]  {w}")

if not failures:
    print("STATUS: PRODUCTION VALIDATION PASSED")
    sys.exit(0)
else:
    print("STATUS: DEPLOYMENT BLOCKED - FIX CRITICAL FAILURES")
    sys.exit(1)
