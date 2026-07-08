"""
setup_supabase.py — One-shot Supabase setup script.
Creates all tables and migrates data from local SQLite.

Usage:
    python setup_supabase.py

Requires SUPABASE_DB_URL in .env
"""
import os
import sys
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def load_env():
    for line in open('.env', encoding='utf-8'):
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

def main():
    load_env()

    supabase_url = os.environ.get("SUPABASE_DB_URL", "")
    local_url    = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")

    if not supabase_url:
        print("""
ERROR: SUPABASE_DB_URL not set in .env

Add this line to your .env file:
    SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.XXXXXX.supabase.co:5432/postgres

Get it from: Supabase → Your Project → Settings → Database → Connection String → Python
""")
        sys.exit(1)

    from sqlalchemy import create_engine, text, inspect
    from core.memory.schema import create_tables

    # Step 1 — Create tables
    print("\n[1/3] Creating GlobalPulse tables in Supabase...")
    dst = create_engine(supabase_url, pool_pre_ping=True, connect_args={"connect_timeout": 30})
    try:
        create_tables(dst)
        print("      Tables created OK")
    except Exception as e:
        print(f"      ERROR: {e}")
        sys.exit(1)

    # Step 2 — Migrate data
    print("\n[2/3] Migrating data from local SQLite -> Supabase...")

    import pandas as pd

    src = create_engine(local_url)
    inspector = inspect(src)
    existing_tables = inspector.get_table_names()

    TABLES = [
        ("teams",                  "id"),
        ("venues",                 "id"),
        ("events",                 "id"),
        ("cricket_match_metadata", "event_id"),
        ("innings",                "id"),
        ("features_statistics",    "event_id"),
        ("features_astronomy",     "event_id"),
        ("features_environment",   "event_id"),
        ("model_registry",         "id"),
        ("experiment_registry",    "id"),
        ("prediction_store",       "id"),
        ("prediction_lineage",     "id"),
    ]

    total = 0
    for table, pk in TABLES:
        if table not in existing_tables:
            print(f"      [{table}] skipped (not in source)")
            continue

        with src.connect() as sc:
            count = sc.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

        if count == 0:
            print(f"      [{table}] skipped (empty)")
            continue

        print(f"      [{table}] migrating {count:,} rows...", end="", flush=True)
        t0 = time.time()

        CHUNK = 250
        migrated = 0
        offset = 0
        
        while True:
            with src.connect() as sc:
                df = pd.read_sql(text(f"SELECT * FROM {table} LIMIT {CHUNK} OFFSET {offset}"), sc)
            
            if df.empty:
                break

            df = df.where(df.notna(), None)
            rows = df.to_dict(orient="records")

            # Use a fresh connection from the engine pool for each chunk to avoid pooler timeouts
            for attempt in range(3):
                try:
                    with dst.begin() as dc:
                        cols = ", ".join(df.columns)
                        params = ", ".join(f":{c}" for c in df.columns)
                        sql = f"INSERT INTO {table} ({cols}) VALUES ({params}) ON CONFLICT DO NOTHING"
                        dc.execute(text(sql), rows)
                    break
                except Exception as e:
                    if attempt == 2:
                        raise e
                    print(f"      [Retry] Connection error on {table}, retrying... ({e})")
                    time.sleep(2)

            migrated += len(df)
            offset += CHUNK

        elapsed = time.time() - t0
        print(f" {migrated:,} rows in {elapsed:.1f}s")
        total += migrated

    # Step 3 — Verify
    print(f"\n[3/3] Verification (Supabase row counts):")
    for table, _ in TABLES:
        try:
            with dst.connect() as dc:
                n = dc.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            status = "[OK]" if n > 0 else "[ 0]"
            print(f"      {status}  {table:<35} {n:>8,}")
        except Exception:
            print(f"      [ERR] {table}")

    print(f"\n   Total migrated: {total:,} rows")
    print("   Raw deliveries: kept local only (too large for Supabase free tier)")
    print("\n   Supabase is ready! Update .env:")
    print(f"   GLOBALPULSE_DB_URL={supabase_url}")
    print("\nDone.")


if __name__ == "__main__":
    main()
