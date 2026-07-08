from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_DB_URL")
engine = create_engine(url)

with engine.connect() as conn:
    print("TOTAL EVENTS:", conn.execute(text("SELECT COUNT(*) FROM events")).fetchone()[0])
    print("TOTAL DELIVERIES:", conn.execute(text("SELECT COUNT(*) FROM deliveries")).fetchone()[0])
    print("TOTAL PLAYERS:", conn.execute(text("SELECT COUNT(*) FROM players")).fetchone()[0])
