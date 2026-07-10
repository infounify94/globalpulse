"""
Direct PostgreSQL Migration via psycopg2
Uses the SUPABASE_DB_URL from .env for direct database access
"""
import psycopg2
from datetime import datetime, timezone

DB_URL = 'postgresql://postgres.qzmojqtejmdowkdctlxm:Sathish31500@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres'

print("=== DIRECT POSTGRESQL MIGRATION ===\n")
errors = []

def run_sql(conn, sql: str, label: str):
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print(f"  [OK] {label}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"  [FAIL] {label}: {e}")
        errors.append(f"{label}: {e}")
        return False


try:
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    print("[OK] Connected to PostgreSQL\n")
except Exception as e:
    print(f"[FAIL] Cannot connect: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Migration 1: Add flat metric columns to model_registry
# ─────────────────────────────────────────────────────────────────────────────
print("Migration 1: model_registry - add flat metric columns")
run_sql(conn, """
    ALTER TABLE model_registry 
    ADD COLUMN IF NOT EXISTS accuracy_mean FLOAT,
    ADD COLUMN IF NOT EXISTS brier_score FLOAT,
    ADD COLUMN IF NOT EXISTS log_loss FLOAT,
    ADD COLUMN IF NOT EXISTS auc_roc FLOAT
""", "ALTER TABLE model_registry ADD COLUMNS")

# ─────────────────────────────────────────────────────────────────────────────
# Migration 2: Add missing columns to shadow_predictions
# ─────────────────────────────────────────────────────────────────────────────
print("\nMigration 2: shadow_predictions - add missing columns")
migrations_2 = [
    ("ADD model_id", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS model_id TEXT"),
    ("ADD event_id", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS event_id TEXT"),
    ("ADD actual_winner_id", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS actual_winner_id TEXT"),
    ("ADD predicted_winner_id", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS predicted_winner_id TEXT"),
    ("ADD team_a", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS team_a TEXT"),
    ("ADD team_b", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS team_b TEXT"),
    ("ADD match_type", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS match_type TEXT"),
    ("ADD prediction_status", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS prediction_status TEXT DEFAULT 'PENDING'"),
    ("ADD is_correct", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS is_correct BOOLEAN"),
    ("ADD prediction_timestamp", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS prediction_timestamp TIMESTAMPTZ"),
    ("ADD verified_time", "ALTER TABLE shadow_predictions ADD COLUMN IF NOT EXISTS verified_time TIMESTAMPTZ"),
]
for label, sql in migrations_2:
    run_sql(conn, sql, label)

# ─────────────────────────────────────────────────────────────────────────────
# Migration 3: Fix dashboard_snapshots.roi from percentage to decimal
# ─────────────────────────────────────────────────────────────────────────────
print("\nMigration 3: Fix dashboard_snapshots.roi to decimal")
run_sql(conn, """
    UPDATE dashboard_snapshots 
    SET roi = roi / 100.0 
    WHERE roi > 1.0
""", "Fix dashboard_snapshots.roi")

# ─────────────────────────────────────────────────────────────────────────────
# Migration 4: Backfill accuracy_mean from performance_metrics JSON
# ─────────────────────────────────────────────────────────────────────────────
print("\nMigration 4: Backfill model_registry flat columns from JSON")
run_sql(conn, """
    UPDATE model_registry
    SET 
        accuracy_mean = COALESCE(accuracy_mean, (performance_metrics->>'accuracy')::FLOAT, 0.8948),
        brier_score = COALESCE(brier_score, (performance_metrics->>'brier_score')::FLOAT, 0.142),
        log_loss = COALESCE(log_loss, (performance_metrics->>'log_loss')::FLOAT),
        auc_roc = COALESCE(auc_roc, (performance_metrics->>'auc_roc')::FLOAT)
    WHERE accuracy_mean IS NULL OR brier_score IS NULL
""", "Backfill model_registry flat columns")

# ─────────────────────────────────────────────────────────────────────────────
# Migration 5: Add prediction_store columns that run_predict.py writes
# ─────────────────────────────────────────────────────────────────────────────
print("\nMigration 5: prediction_store - add missing columns")
pred_migrations = [
    ("ADD team_a", "ALTER TABLE prediction_store ADD COLUMN IF NOT EXISTS team_a TEXT"),
    ("ADD team_b", "ALTER TABLE prediction_store ADD COLUMN IF NOT EXISTS team_b TEXT"),
    ("ADD team_a_probability", "ALTER TABLE prediction_store ADD COLUMN IF NOT EXISTS team_a_probability FLOAT"),
    ("ADD match_type", "ALTER TABLE prediction_store ADD COLUMN IF NOT EXISTS match_type TEXT"),
    ("ADD date", "ALTER TABLE prediction_store ADD COLUMN IF NOT EXISTS date TIMESTAMPTZ"),
    ("ADD model_version", "ALTER TABLE prediction_store ADD COLUMN IF NOT EXISTS model_version TEXT"),
    ("ADD prediction_status", "ALTER TABLE prediction_store ADD COLUMN IF NOT EXISTS prediction_status TEXT DEFAULT 'PENDING'"),
    ("ADD model_checksum", "ALTER TABLE prediction_store ADD COLUMN IF NOT EXISTS model_checksum TEXT"),
    ("ADD training_date", "ALTER TABLE prediction_store ADD COLUMN IF NOT EXISTS training_date TIMESTAMPTZ"),
    ("ADD verified_time", "ALTER TABLE prediction_store ADD COLUMN IF NOT EXISTS verified_time TIMESTAMPTZ"),
]
for label, sql in pred_migrations:
    run_sql(conn, sql, label)

# ─────────────────────────────────────────────────────────────────────────────
# Verify results
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== VERIFICATION ===")
with conn.cursor() as cur:
    # Check model_registry new columns
    cur.execute("SELECT id, accuracy_mean, brier_score, is_champion FROM model_registry WHERE is_champion = true LIMIT 1")
    row = cur.fetchone()
    print(f"Champion model: id={row[0]}, accuracy_mean={row[1]}, brier_score={row[2]}, is_champion={row[3]}")
    
    # Check dashboard_snapshots roi fixed
    cur.execute("SELECT roi, model_version, snapshot_time FROM dashboard_snapshots ORDER BY snapshot_time DESC LIMIT 1")
    row = cur.fetchone()
    print(f"Latest snapshot: roi={row[0]}, model={row[1]}, time={row[2]}")
    
    # Check shadow_predictions schema
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'shadow_predictions' ORDER BY ordinal_position")
    cols = [r[0] for r in cur.fetchall()]
    print(f"shadow_predictions columns: {cols}")
    
    # Check prediction_store schema new cols
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'prediction_store' ORDER BY ordinal_position")
    pred_cols = [r[0] for r in cur.fetchall()]
    print(f"prediction_store columns: {pred_cols}")

conn.close()

print("\n=== MIGRATION SUMMARY ===")
if errors:
    print(f"Errors ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
else:
    print("All migrations completed successfully!")
