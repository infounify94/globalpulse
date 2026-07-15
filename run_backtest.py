import os
import sys

# Ensure Python can find the core module
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.agents.research_pipeline.walk_forward_trainer import WalkForwardTrainer
from core.agents.super_agent import CatBoostSuperAgent

DB_PATH = os.path.join(BASE_DIR, "data", "datasets", "cricsheet", "cricsheet_datalake.db")

def main():
    print("Initializing Walk-Forward Trainer...")
    trainer = WalkForwardTrainer(db_path=DB_PATH, model_class=CatBoostSuperAgent)
    
    print("\nStarting Walk-Forward Loop (Train 4 years, Test 1 year)...")
    # For speed of validation we use a larger train window and step forward
    trainer.run_validation(train_window_years=4, test_window_years=1)

if __name__ == "__main__":
    main()
