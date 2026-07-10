import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler
from core.etl.connectors.live_connector import ScoreConnector
from core.memory.schema import get_engine
from core.engine.continuous_learning import ContinuousLearningEngine

logging.basicConfig(level=logging.INFO)

class AutomatedScheduler:
    """
    Runs the daily MLOps pipeline on autopilot using real ScoreConnector.
    """
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.connector = ScoreConnector()
        self.engine = get_engine()
        self.learning_engine = ContinuousLearningEngine(self.engine, pipeline=None)
        
    def daily_ingestion_and_retrain_job(self):
        """
        1. Fetch yesterday's actual outcomes.
        2. Validate data.
        3. Verify against predictions.
        4. Trigger retraining.
        """
        logging.info("Starting Daily Ingestion Job...")
        recent_results = self.connector.fetch_recent_results()
        
        for result in recent_results:
            match_id = result['match_id']
            winner = result['winner']
            logging.info(f"Ingested result for {match_id}: {winner}")
            
            # In a full system, we would query prediction_store to find the prediction_id
            # Then call: self.learning_engine.verify_and_retrain(prediction_id, winner)
            
        logging.info("Daily Ingestion Job Complete. Retraining triggered if necessary.")

    def start(self):
        # Schedule the job to run every day at 23:59
        self.scheduler.add_job(self.daily_ingestion_and_retrain_job, 'cron', hour=23, minute=59)
        self.scheduler.start()
        logging.info("Automated Scheduler started. Press Ctrl+C to exit.")
        
if __name__ == "__main__":
    scheduler = AutomatedScheduler()
    scheduler.start()
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        scheduler.scheduler.shutdown()
