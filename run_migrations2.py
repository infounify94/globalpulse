"""
Production Migrations — Round 2
Complete remaining fixes with pagination to handle Supabase 1000-row limit.
"""
import os, sys, json
from datetime import datetime, timezone

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ['SUPABASE_URL'] = 'https://qzmojqtejmdowkdctlxm.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6bW9qcXRlam1kb3drZGN0bHhtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzQyODgwNCwiZXhwIjoyMDk5MDA0ODA0fQ.SBOA0gNLvMLNJGW13fSS8uj8tb7KLvrbbUBDfSnNYUM'

from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

print("=" * 60)
print("MIGRATION 1b: Fix remaining VERIFIED rows with null actual_winner")
print("=" * 60)

total_fixed = 0
pass_num = 0
while True:
    pass_num += 1
    r = sb.table('prediction_store') \
          .select('id') \
          .eq('prediction_status', 'VERIFIED') \
          .is_('actual_winner_id', 'null') \
          .limit(500) \
          .execute()

    bad_ids = [row['id'] for row in (r.data or [])]
    if not bad_ids:
        print(f"  Pass {pass_num}: No more bad rows. Done.")
        break

    upd = sb.table('prediction_store') \
             .update({'prediction_status': 'PENDING'}) \
             .in_('id', bad_ids) \
             .execute()
    total_fixed += len(bad_ids)
    print(f"  Pass {pass_num}: Fixed {len(bad_ids)} rows (cumulative: {total_fixed})")

print(f"  Total fixed this run: {total_fixed}")

# Final verification
r = sb.table('prediction_store') \
      .select('id', count='exact') \
      .eq('prediction_status', 'VERIFIED') \
      .is_('actual_winner_id', 'null') \
      .execute()
remaining = r.count
print(f"  Remaining VERIFIED+null: {remaining} (must be 0)")

print()
print("=" * 60)
print("MIGRATION 2b: Delete ALL remaining mock shadow_predictions")
print("=" * 60)

all_deleted = 0
pass_num = 0
while True:
    pass_num += 1
    r = sb.table('shadow_predictions').select('id, match_id').execute()
    all_sp = r.data or []
    mock_rows = [row for row in all_sp if
                 'mock' in str(row.get('match_id', '')).lower() or
                 str(row.get('match_id', '')).startswith('live_')]
    if not mock_rows:
        print(f"  Pass {pass_num}: No more mock rows. Done.")
        break
    mock_ids = [row['id'] for row in mock_rows]
    sb.table('shadow_predictions').delete().in_('id', mock_ids).execute()
    all_deleted += len(mock_ids)
    print(f"  Pass {pass_num}: Deleted {len(mock_ids)} rows")

r = sb.table('shadow_predictions').select('id', count='exact').execute()
sp_count = r.count
print(f"  shadow_predictions remaining: {sp_count}")

print()
print("=" * 60)
print("MIGRATION 3: Compute confidence buckets from prediction_store")
print("=" * 60)

# We'll compute these client-side and push into dashboard_snapshots
# Pull all predictions with confidence values
print("  Fetching all confidence values from prediction_store...")
r = sb.table('prediction_store') \
      .select('confidence') \
      .not_.is_('confidence', 'null') \
      .limit(20000) \
      .execute()
conf_rows = r.data or []
print(f"  Rows with confidence values: {len(conf_rows)}")

high = sum(1 for row in conf_rows if (row.get('confidence') or 0) >= 0.8)
medium = sum(1 for row in conf_rows if 0.6 <= (row.get('confidence') or 0) < 0.8)
low = sum(1 for row in conf_rows if 0.4 <= (row.get('confidence') or 0) < 0.6)
very_low = sum(1 for row in conf_rows if (row.get('confidence') or 0) < 0.4)
total_with_conf = len(conf_rows)

print(f"  Confidence buckets computed:")
print(f"    high (>=0.8):       {high}")
print(f"    medium (0.6-0.8):   {medium}")
print(f"    low (0.4-0.6):      {low}")
print(f"    very_low (<0.4):    {very_low}")
print(f"    total_with_conf:    {total_with_conf}")

# Note: We cannot modify the dashboard_summary VIEW definition via Supabase client API.
# We will instead serve the confidence buckets from a separate endpoint in endpoints.js
# by computing them directly from prediction_store.
# Store the computation result for the frontend endpoints patch.
bucket_data = {
    'high_confidence': high,
    'medium_confidence': medium,
    'low_confidence': low,
    'very_low': very_low,
    'total_with_confidence': total_with_conf
}
print(f"\n  Bucket data to serve from separate query: {bucket_data}")

print()
print("=" * 60)
print("FINAL VALIDATION")
print("=" * 60)

r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'PENDING').execute()
pending = r.count
r2 = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'VERIFIED').execute()
verified = r2.count
r3 = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'VERIFIED').is_('actual_winner_id', 'null').execute()
bad_v = r3.count
r4 = sb.table('shadow_predictions').select('id', count='exact').execute()
sp = r4.count
r5 = sb.table('model_registry').select('id', count='exact').eq('is_champion', True).execute()
champs = r5.count

print(f"  prediction_store PENDING:  {pending}")
print(f"  prediction_store VERIFIED: {verified}")
print(f"  VERIFIED+null actual:      {bad_v}  (must be 0)")
print(f"  shadow_predictions:        {sp}")
print(f"  Champion models:           {champs}  (must be 1)")

checks = [
    ("VERIFIED+null actual == 0", bad_v == 0),
    ("Exactly 1 champion", champs == 1),
]
all_pass = all(c[1] for c in checks)
for label, passed in checks:
    marker = "PASS" if passed else "FAIL"
    print(f"  [{marker}] {label}")

print()
print("MIGRATIONS COMPLETE:", "ALL PASSED" if all_pass else "SOME ISSUES REMAIN")
