import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory.schema import Base, DBTeam, DBPlayer, DBVenue, DBEvent, DBCricketMatchMetadata
from core.memory.schema import DBFeatureStatistics, DBFeatureAstronomy, DBFeatureEnvironment
from core.memory.schema import DBFeatureVedic, DBFeatureBabylonian, DBFeatureNumerology, DBFeaturePanchaBhuta
from core.memory.schema import DBFeatureRegistry, DBExperimentRegistry, DBModelRegistry
from core.memory.schema import DBShadowPrediction, DBPredictionAudit, DBShadowMetric

def migrate():
    sqlite_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
    pg_url = os.environ.get("SUPABASE_DB_URL")

    if not pg_url:
        print("Error: SUPABASE_DB_URL is not set in .env")
        return

    print(f"Connecting to SQLite: {sqlite_url}")
    sqlite_engine = create_engine(sqlite_url)
    
    # Handle Supabase connection pooler issue with SQLAlchemy (requires dialect adjustment if needed, but psycopg2 usually handles it)
    print(f"Connecting to PostgreSQL: {pg_url}")
    pg_engine = create_engine(pg_url)

    # Create all tables in Postgres
    print("Dropping existing tables in PostgreSQL to ensure fresh schema...")
    Base.metadata.drop_all(pg_engine)
    print("Creating tables in PostgreSQL...")
    Base.metadata.create_all(pg_engine)

    # Tables to migrate (excluding DBDelivery and DBInning to save time and space on free tier)
    tables_to_migrate = [
        DBTeam, DBPlayer, DBVenue, DBEvent, DBCricketMatchMetadata,
        DBFeatureStatistics, DBFeatureAstronomy, DBFeatureEnvironment,
        DBFeatureVedic, DBFeatureBabylonian, DBFeatureNumerology, DBFeaturePanchaBhuta,
        DBFeatureRegistry, DBExperimentRegistry, DBModelRegistry,
        DBShadowPrediction, DBPredictionAudit, DBShadowMetric
    ]

    with Session(sqlite_engine) as sqlite_session:
        with Session(pg_engine) as pg_session:
            for table in tables_to_migrate:
                table_name = table.__tablename__
                print(f"Migrating {table_name}...")
                
                # Check if already migrated
                pg_count = pg_session.query(table).count()
                if pg_count > 0:
                    print(f"  -> Skipping {table_name}, already contains {pg_count} records in PG.")
                    continue
                
                # Fetch from sqlite
                records = sqlite_session.query(table).all()
                if not records:
                    print(f"  -> No records found in SQLite for {table_name}.")
                    continue
                
                print(f"  -> Copying {len(records)} records...")
                
                # Expunge from sqlite session so we can add to pg session
                for r in records:
                    sqlite_session.expunge(r)
                
                # Batch insert
                batch_size = 5000
                for i in range(0, len(records), batch_size):
                    batch = records[i:i+batch_size]
                    pg_session.add_all(batch)
                    pg_session.commit()
                
                print(f"  -> {table_name} migration complete.")

    print("Migration finished successfully!")

if __name__ == "__main__":
    migrate()
