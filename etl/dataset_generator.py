import os
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.memory.schema import get_engine
from core.engine.base_trainer import BaseTrainer

# Need to install pandas and pyarrow to save to parquet
try:
    import pandas as pd
except ImportError:
    logging.warning("pandas not installed. Cannot generate parquet datasets.")
    pd = None

class WalkForwardDatasetGenerator:
    """
    Generates static parquet datasets for walk-forward validation.
    Materializes the features and outcomes from the database into flat files.
    """
    
    def __init__(self, engine, output_dir="datasets"):
        self.engine = engine
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_datasets(self, start_year: int, end_year: int, step_years: int = 1):
        if not pd:
            raise ImportError("pandas and pyarrow are required for dataset generation")
            
        # Use the logic from BaseTrainer
        class TempTrainer(BaseTrainer):
            def train_walk_forward(self, historical_events, validation_steps): pass
            def get_feature_importance(self): return {}
            
        trainer = TempTrainer(None)
        splits = trainer.generate_walk_forward_splits(start_year, end_year, step_years)
        
        with Session(self.engine) as session:
            # Query all necessary joined data
            # This is a simplification; in production, you would join feature_statistics and feature_astronomy
            query = """
            SELECT 
                e.id, e.date, e.venue_id, e.outcome,
                m.team_a_id, m.team_b_id,
                fs.features as stat_features,
                fa.features as astro_features
            FROM events e
            JOIN cricket_match_metadata m ON e.id = m.event_id
            LEFT JOIN features_statistics fs ON e.id = fs.event_id
            LEFT JOIN features_astronomy fa ON e.id = fa.event_id
            WHERE e.event_type = 'cricket'
            """
            
            # Note: Pandas read_sql natively handles SQLAlchemy sessions
            logging.info("Querying database for full feature set...")
            df = pd.read_sql(text(query), session.bind)
            
            # Expand JSON features into columns if needed, but for now we just
            # want to slice the main DataFrame chronologically
            df['date'] = pd.to_datetime(df['date'])
            df['year'] = df['date'].dt.year
            
            for split in splits:
                train_start = split['train_start_year']
                train_end = split['train_end_year']
                test_start = split['test_start_year']
                test_end = split['test_end_year']
                
                # Slicing
                train_df = df[(df['year'] >= train_start) & (df['year'] <= train_end)]
                test_df = df[(df['year'] >= test_start) & (df['year'] <= test_end)]
                
                # Save to Parquet
                train_file = os.path.join(self.output_dir, f"train_{train_start}_{train_end}.parquet")
                test_file = os.path.join(self.output_dir, f"test_{test_start}_{test_end}.parquet")
                
                train_df.to_parquet(train_file, engine='pyarrow')
                test_df.to_parquet(test_file, engine='pyarrow')
                
                logging.info(f"Generated {train_file} ({len(train_df)} rows)")
                logging.info(f"Generated {test_file} ({len(test_df)} rows)")
                
        logging.info("Dataset generation complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse.db")
    engine = get_engine(db_url)
    
    generator = WalkForwardDatasetGenerator(engine)
    try:
        generator.generate_datasets(2008, 2023, step_years=1)
    except Exception as e:
        logging.error(f"Failed to generate datasets: {e}")
