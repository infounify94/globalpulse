import os
import uuid
import logging
from core.memory.schema import get_engine, Base
from core.engine.pipeline import TrainingPipeline
from core.engine.models.xgboost_trainer import XGBoostTrainer
from core.engine.models.sklearn_trainers import LogisticRegressionTrainer
from core.reporting.dashboard import DashboardGenerator
from etl.dataset_generator import WalkForwardDatasetGenerator

logging.basicConfig(level=logging.INFO)

def run():
    # Connect to database (Supabase by default)
    db_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    
    # 1. Generate real datasets from the Database
    logging.info("Generating Walk-Forward datasets from database...")
    generator = WalkForwardDatasetGenerator(engine, output_dir="datasets")
    # For cricket, we train on historical and test on a recent year
    generator.generate_datasets(start_year=2008, end_year=2024, step_years=2)
    
    # Locate the generated files
    train_files = [f for f in os.listdir("datasets") if f.startswith("train_") and f.endswith(".parquet")]
    test_files = [f for f in os.listdir("datasets") if f.startswith("test_") and f.endswith(".parquet")]
    
    # 2. Pipeline Orchestrator
    pipeline = TrainingPipeline(engine, dataset_dir="datasets")
    
    # 3. Run the Experiment
    experiment_id = f"exp_{str(uuid.uuid4())[:8]}"
    
    try:
        pipeline.run_experiment(
            experiment_id=experiment_id,
            train_files=train_files,
            test_files=test_files,
            trainers=[LogisticRegressionTrainer(), XGBoostTrainer()],
            feature_families=["statistics", "statistics,astronomy"],
            use_optuna=True,
            optuna_trials=30  # High accuracy tuning
        )
        
        # 4. Generate the Dashboard
        dashboard = DashboardGenerator(engine, "reports")
        report_path = dashboard.generate_experiment_report(experiment_id)
        
        logging.info(f"Pipeline complete! Report generated at: {report_path}")
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")

if __name__ == "__main__":
    run()
