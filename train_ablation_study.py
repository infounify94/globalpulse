import os
import uuid
import logging
from core.memory.schema import get_engine, Base
from core.engine.pipeline import TrainingPipeline
from core.engine.models.xgboost_trainer import XGBoostTrainer
from core.engine.models.catboost_trainer import CatBoostTrainer
from core.engine.models.lightgbm_trainer import LightGBMTrainer
from core.engine.models.sklearn_trainers import RandomForestTrainer, LogisticRegressionTrainer
from etl.dataset_generator import WalkForwardDatasetGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_ablation_study():
    db_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
    engine = get_engine(db_url)
    
    # 1. Generate updated datasets
    logging.info("Generating Walk-Forward datasets...")
    generator = WalkForwardDatasetGenerator(engine, output_dir="datasets")
    generator.generate_datasets(start_year=2008, end_year=2024, step_years=2)
    
    train_files = [f for f in os.listdir("datasets") if f.startswith("train_") and f.endswith(".parquet")]
    test_files = [f for f in os.listdir("datasets") if f.startswith("test_") and f.endswith(".parquet")]
    
    pipeline = TrainingPipeline(engine, dataset_dir="datasets")
    experiment_id = f"sci_audit_{str(uuid.uuid4())[:8]}"
    
    feature_families = [
        "statistics",
        "statistics,vedic",
        "statistics,babylonian",
        "statistics,numerology",
        "statistics,pancha_bhuta",
        "statistics,environment",
        "statistics,astronomy",
        "statistics,astronomy,environment,vedic,babylonian,numerology,pancha_bhuta"
    ]
    
    trainers = [
        XGBoostTrainer(random_seed=42),
        CatBoostTrainer(random_seed=42),
        LightGBMTrainer(random_seed=42),
        RandomForestTrainer(random_seed=42),
        LogisticRegressionTrainer(random_seed=42)
    ]
    
    logging.info(f"Starting Scientific Audit Experiment: {experiment_id}")
    
    pipeline.run_experiment(
        experiment_id=experiment_id,
        train_files=train_files,
        test_files=test_files,
        trainers=trainers,
        feature_families=feature_families,
        use_optuna=False,
    )
    
    logging.info("Scientific Audit completed successfully.")

if __name__ == "__main__":
    run_ablation_study()
