"""
migrate_to_supabase.py
Migrates all important tables from local SQLite → Supabase PostgreSQL.
Deliberately EXCLUDES raw deliveries (too large, not needed in cloud).

Usage:
    python migrate_to_supabase.py

Set in .env before running:
    GLOBALPULSE_DB_URL=sqlite:///globalpulse_dev.db          (source)
    SUPABASE_DB_URL=postgresql://postgres:[password]@db.xxx.supabase.co:5432/postgres  (target)
"""
import os
import sys
import logging
import pandas as pd
from sqlalchemy import create_engine, text, inspect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Tables to migrate to Supabase (raw deliveries are excluded — too large)
TABLES_TO_MIGRATE = [
    "teams",
    "venues",
    "events",
    "cricket_match_metadata",
    "innings",
    "features_statistics",
    "features_astronomy",
    "features_environment",
    "feature_registry",
    "experiment_registry",
    "model_registry",
    "prediction_store",
    "prediction_lineage",
]

CHUNK_SIZE = 500  # rows per batch insert


def get_table_count(engine, table: str) -> int:
    try:
        with engine.connect() as conn:
            return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    except Exception:
        return 0


def table_exists(engine, table: str) -> bool:
    inspector = inspect(engine)
    return table in inspector.get_table_names()


def migrate_table(src_engine, dst_engine, table: str):
    src_count = get_table_count(src_engine, table)
    if src_count == 0:
        logging.info(f"  [{table}] SKIPPED (empty)")
        return 0

    logging.info(f"  [{table}] Migrating {src_count:,} rows...")

    migrated = 0
    with src_engine.connect() as src_conn:
        # Read in chunks to handle large tables
        offset = 0
        while True:
            df = pd.read_sql(
                text(f"SELECT * FROM {table} LIMIT {CHUNK_SIZE} OFFSET {offset}"),
                src_conn
            )
            if df.empty:
                break

            # Write to Supabase with ON CONFLICT DO NOTHING
            with dst_engine.begin() as dst_conn:
                for _, row in df.iterrows():
                    cols = ", ".join(df.columns)
                    placeholders = ", ".join(f":{c}" for c in df.columns)
                    sql = (
                        f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) "
                        f"ON CONFLICT DO NOTHING"
                    )
                    try:
                        dst_conn.execute(text(sql), row.to_dict())
                    except Exception as e:
                        logging.warning(f"    Row insert failed: {e}")

            migrated += len(df)
            offset += CHUNK_SIZE

            pct = (migrated / src_count) * 100
            print(f"\r    Progress: {migrated:,}/{src_count:,} ({pct:.0f}%)", end="", flush=True)

    print()  # newline after progress
    logging.info(f"  [{table}] Done — {migrated:,} rows migrated")
    return migrated


def main():
    # Load .env
    for line in open('.env'):
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

    src_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
    dst_url = os.environ.get("SUPABASE_DB_URL", "")

    if not dst_url:
        print("""
ERROR: SUPABASE_DB_URL not set in .env

To get it:
  1. Go to supabase.com → your project
  2. Settings → Database → Connection String → Python (SQLAlchemy)
  3. Copy the connection string
  4. Add to .env:
     SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
""")
        sys.exit(1)

    logging.info(f"Source: {src_url.split('//')[1].split('/')[0]}")
    logging.info(f"Target: {dst_url.split('@')[1] if '@' in dst_url else dst_url}")

    src_engine = create_engine(src_url)
    dst_engine = create_engine(dst_url, pool_pre_ping=True)

    # Ensure Supabase tables exist
    logging.info("Creating tables in Supabase...")
    from core.memory.schema import create_tables
    create_tables(dst_engine)
    logging.info("Tables ready.")

    # Migrate each table
    total_rows = 0
    for table in TABLES_TO_MIGRATE:
        if not table_exists(src_engine, table):
            logging.info(f"  [{table}] SKIPPED (not in source)")
            continue
        try:
            rows = migrate_table(src_engine, dst_engine, table)
            total_rows += rows
        except Exception as e:
            logging.error(f"  [{table}] FAILED: {e}")

    # Show final stats
    print("\n" + "=" * 55)
    print("MIGRATION COMPLETE")
    print("=" * 55)
    print(f"Total rows migrated: {total_rows:,}")
    print("\nSupabase table counts:")
    for table in TABLES_TO_MIGRATE:
        if table_exists(dst_engine, table):
            count = get_table_count(dst_engine, table)
            status = "[OK]" if count > 0 else "[ 0]"
            print(f"  {status}  {table:<35} {count:>8}")

    print("\nNote: raw deliveries table was intentionally NOT migrated.")
    print("Deliveries are only needed locally for feature generation.")
    print("=" * 55)


if __name__ == "__main__":
    main()
