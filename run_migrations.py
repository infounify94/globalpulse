"""
Production SQL Migrations — GlobalPulse
Executes all 3 migrations against Supabase production database.
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
print("MIGRATION 1: Reset VERIFIED→PENDING for null actual_winner")
print("=" * 60)

# Step 1a: Get IDs of all bad rows (VERIFIED + null actual_winner)
r = sb.table('prediction_store') \
      .select('id') \
      .eq('prediction_status', 'VERIFIED') \
      .is_('actual_winner_id', 'null') \
      .execute()

bad_ids = [row['id'] for row in (r.data or [])]
print(f"  Found {len(bad_ids)} VERIFIED rows with null actual_winner_id")

# Step 1b: Update in batches of 500
BATCH = 500
updated = 0
for i in range(0, len(bad_ids), BATCH):
    batch = bad_ids[i:i + BATCH]
    upd = sb.table('prediction_store') \
             .update({'prediction_status': 'PENDING'}) \
             .in_('id', batch) \
             .execute()
    updated += len(batch)
    print(f"  Updated batch {i//BATCH + 1}: {len(batch)} rows (total so far: {updated})")

print(f"  Migration 1 complete: {updated} rows reset to PENDING")

# Verify
r = sb.table('prediction_store') \
      .select('id', count='exact') \
      .eq('prediction_status', 'VERIFIED') \
      .is_('actual_winner_id', 'null') \
      .execute()
remaining_bad = r.count
print(f"  Verification — VERIFIED with null actual_winner: {remaining_bad} (expected 0)")

print()
print("=" * 60)
print("MIGRATION 2: Delete mock shadow_predictions rows")
print("=" * 60)

# Get all shadow_predictions match_ids first
r = sb.table('shadow_predictions').select('id, match_id').execute()
all_sp = r.data or []
mock_rows = [row for row in all_sp if 'mock' in str(row.get('match_id', '')).lower()]
print(f"  Total shadow_predictions: {len(all_sp)}")
print(f"  Mock rows to delete: {len(mock_rows)}")

if mock_rows:
    mock_ids = [row['id'] for row in mock_rows]
    del_result = sb.table('shadow_predictions').delete().in_('id', mock_ids).execute()
    print(f"  Deleted {len(mock_ids)} mock shadow_predictions rows")
else:
    print("  No mock rows found")

# Verify
r = sb.table('shadow_predictions').select('id', count='exact').execute()
remaining_sp = r.count
print(f"  Verification — shadow_predictions remaining: {remaining_sp}")

print()
print("=" * 60)
print("MIGRATION 3: Check dashboard_snapshots schema")
print("=" * 60)

# Probe dashboard_snapshots columns
r = sb.table('dashboard_snapshots').select('*').limit(1).execute()
if r.data:
    cols = list(r.data[0].keys())
    print(f"  dashboard_snapshots columns: {cols}")
    print(f"  Sample: {json.dumps(r.data[0], default=str)[:400]}")
else:
    print("  dashboard_snapshots: empty or inaccessible")

print()
print("=" * 60)
print("MIGRATION 3b: Check current dashboard_summary view definition")
print("=" * 60)

r = sb.table('dashboard_summary').select('*').limit(1).execute()
if r.data:
    cols = list(r.data[0].keys())
    print(f"  dashboard_summary columns: {cols}")
    print(f"  Values: {json.dumps(r.data[0], default=str)}")
else:
    print("  dashboard_summary: no data")

print()
print("=" * 60)
print("POST-MIGRATION VALIDATION")
print("=" * 60)

# Final counts
r = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'PENDING').execute()
pending = r.count
r2 = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'VERIFIED').execute()
verified = r2.count
print(f"  PENDING predictions: {pending}")
print(f"  VERIFIED predictions: {verified}")

now_iso = datetime.now(timezone.utc).isoformat()
r3 = sb.table('prediction_store').select('id', count='exact').eq('prediction_status', 'VERIFIED').is_('actual_winner_id', 'null').execute()
bad_verified = r3.count
print(f"  VERIFIED with null actual_winner: {bad_verified} (must be 0)")

r4 = sb.table('shadow_predictions').select('id', count='exact').execute()
sp_count = r4.count
print(f"  shadow_predictions total: {sp_count}")

r5 = sb.table('model_registry').select('id', count='exact').eq('is_champion', True).execute()
champ_count = r5.count
print(f"  Champion models: {champ_count} (must be 1)")

print()
print("MIGRATION SUMMARY")
print("-" * 40)
all_ok = (bad_verified == 0 and champ_count == 1)
print("  Status:", "PASSED" if all_ok else "ISSUES REMAIN")
print("Done.")
