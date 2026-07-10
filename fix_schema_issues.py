"""
Fix remaining schema issues:
1. Add 'confidence' column to shadow_predictions (it has 'confidence_bucket' but not 'confidence')
2. Find the base table for dashboard_summary VIEW and update it directly
"""
import psycopg2

DB_URL = 'postgresql://postgres.qzmojqtejmdowkdctlxm:Sathish31500@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres'
conn = psycopg2.connect(DB_URL)

print("=== FIX SCHEMA ISSUES ===\n")

with conn.cursor() as cur:
    # 1. Add confidence column to shadow_predictions
    print("1. Add confidence column to shadow_predictions:")
    cur.execute("""
        ALTER TABLE shadow_predictions 
        ADD COLUMN IF NOT EXISTS confidence FLOAT
    """)
    conn.commit()
    print("   [OK] confidence column added")
    
    # 2. Check what VIEW definition dashboard_summary uses
    print("\n2. Inspect dashboard_summary view definition:")
    cur.execute("""
        SELECT definition 
        FROM pg_views 
        WHERE viewname = 'dashboard_summary' AND schemaname = 'public'
    """)
    row = cur.fetchone()
    if row:
        print(f"   VIEW definition: {row[0][:500]}")
    else:
        print("   dashboard_summary is NOT a view - checking as table")
        cur.execute("""
            SELECT table_type FROM information_schema.tables 
            WHERE table_name = 'dashboard_summary' AND table_schema = 'public'
        """)
        t = cur.fetchone()
        print(f"   Table type: {t}")

    # 3. Check dashboard_snapshots structure
    print("\n3. dashboard_snapshots structure:")
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'dashboard_snapshots' AND table_schema = 'public'
        ORDER BY ordinal_position
    """)
    cols = cur.fetchall()
    for c in cols:
        print(f"   {c[0]}: {c[1]}")

    # 4. Check if dashboard_summary is built from dashboard_snapshots
    print("\n4. dashboard_summary columns:")
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'dashboard_summary' AND table_schema = 'public'
        ORDER BY ordinal_position
    """)
    ds_cols = cur.fetchall()
    for c in ds_cols:
        print(f"   {c[0]}: {c[1]}")

    # 5. Check current dashboard_summary data
    print("\n5. Current dashboard_summary data:")
    cur.execute("SELECT * FROM dashboard_summary LIMIT 1")
    row = cur.fetchone()
    desc = [d[0] for d in cur.description]
    if row:
        for k, v in zip(desc, row):
            print(f"   {k}: {v}")

conn.close()
print("\nDone.")
