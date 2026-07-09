import sys
import os
import json
import logging
from datetime import datetime

# Setup paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from sqlalchemy import text
from core.memory.schema import (
    get_engine, DBEvent, DBCricketMatchMetadata, DBVenue, DBTeam,
    DBFeatureVedic, DBFeatureBabylonian, DBFeatureNumerology, DBFeaturePanchaBhuta
)
from core.engine.ancient_raw_generator import generate_all_ancient_raw

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def backfill_ancient_features():
    db_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
    engine = get_engine(db_url)
    
    with Session(engine) as session:
        # Get all cricket matches that don't have ancient features generated yet
        # We can just upsert, but checking count is good.
        logging.info("Querying historical cricket matches...")
        
        # We need event_id, date, venue name, team A name, team B name
        query = """
        SELECT 
            e.id as event_id, e.date as match_date, v.name as venue_name,
            t1.name as team_a_name, t2.name as team_b_name
        FROM events e
        JOIN cricket_match_metadata m ON e.id = m.event_id
        LEFT JOIN venues v ON e.venue_id = v.id
        JOIN teams t1 ON m.team_a_id = t1.id
        JOIN teams t2 ON m.team_b_id = t2.id
        WHERE e.event_type = 'cricket'
        """
        
        result = session.execute(text(query)).fetchall()
        total = len(result)
        logging.info(f"Found {total} historical matches. Generating raw ancient features...")
        
        count = 0
        for row in result:
            event_id, match_date_str, venue_name, team_a, team_b = row
            venue = venue_name or "Unknown"
            
            # parse date
            try:
                # Some dates are stored as datetime strings
                if isinstance(match_date_str, str):
                    match_date = datetime.strptime(match_date_str.split(" ")[0], "%Y-%m-%d").date()
                else:
                    match_date = match_date_str.date() # if it's already a datetime object
            except Exception:
                continue
                
            features = generate_all_ancient_raw(match_date, venue, team_a, team_b)
            
            # Upsert into DBFeatureVedic
            vedic = session.query(DBFeatureVedic).filter_by(event_id=event_id).first()
            if not vedic:
                vedic = DBFeatureVedic(event_id=event_id)
                session.add(vedic)
            vedic.features = features["vedic"]
            
            # Upsert into DBFeatureBabylonian
            babylonian = session.query(DBFeatureBabylonian).filter_by(event_id=event_id).first()
            if not babylonian:
                babylonian = DBFeatureBabylonian(event_id=event_id)
                session.add(babylonian)
            babylonian.features = features["babylonian"]
            
            # Upsert into DBFeatureNumerology
            numerology = session.query(DBFeatureNumerology).filter_by(event_id=event_id).first()
            if not numerology:
                numerology = DBFeatureNumerology(event_id=event_id)
                session.add(numerology)
            numerology.features = features["numerology"]
            
            # Upsert into DBFeaturePanchaBhuta
            pancha = session.query(DBFeaturePanchaBhuta).filter_by(event_id=event_id).first()
            if not pancha:
                pancha = DBFeaturePanchaBhuta(event_id=event_id)
                session.add(pancha)
            pancha.features = features["pancha_bhuta"]
            
            count += 1
            if count % 1000 == 0:
                logging.info(f"Processed {count}/{total} matches...")
                session.commit()
                
        session.commit()
        logging.info(f"Successfully generated ancient features for {count} matches.")

if __name__ == "__main__":
    backfill_ancient_features()
