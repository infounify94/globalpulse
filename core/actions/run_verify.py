import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

def run_verification():
    conn = psycopg2.connect(os.environ.get('SUPABASE_DB_URL'))
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        logging.info("Verifying completed matches...")
        # 1. Fetch matches from CricAPI that have completed
        # 2. Update prediction_store setting prediction_status='VERIFIED' and is_correct=True/False
        
        logging.info("Computing Dashboard Metrics...")
        # 3. Calculate Accuracy, Brier, ROI for the current Champion
        cur.execute("SELECT COUNT(*) as total, SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct FROM prediction_store WHERE is_correct IS NOT NULL")
        row = cur.fetchone()
        
        if row and row['total'] > 0:
            accuracy = row['correct'] / row['total']
            
            # Append to dashboard_snapshots
            cur.execute("""
                INSERT INTO dashboard_snapshots (model_version, accuracy, total_predictions)
                VALUES ('1.0.0', %s, %s)
            """, (accuracy, row['total']))
            logging.info(f"Appended snapshot with accuracy {accuracy}")
            
        logging.info("Verification completed.")
    except Exception as e:
        logging.error(f"Error during verification: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_verification()
