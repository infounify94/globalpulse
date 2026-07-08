import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("SUPABASE_DB_URL", "sqlite:///globalpulse.db")
engine = create_engine(db_url)

with engine.connect() as conn:
    events = conn.execute(text("SELECT COUNT(*) FROM events")).scalar()
    metadata = conn.execute(text("SELECT COUNT(*) FROM cricket_match_metadata")).scalar()
    innings = conn.execute(text("SELECT COUNT(*) FROM innings")).scalar()
    deliveries = conn.execute(text("SELECT COUNT(*) FROM deliveries")).scalar()
    stats = conn.execute(text("SELECT COUNT(*) FROM features_statistics")).scalar()

    print(f"Events: {events}")
    print(f"Metadata: {metadata}")
    print(f"Innings: {innings}")
    print(f"Deliveries: {deliveries}")
    print(f"Features: {stats}")
