import os
import uuid
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from core.memory.schema import (
    DBExperimentRegistry, DBModelRegistry, DBFeatureRegistry, DBPredictionStore
)
from sqlalchemy.orm import Session

def load_env():
    for line in open('.env', encoding='utf-8'):
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

def main():
    load_env()
    supabase_url = os.environ.get("SUPABASE_DB_URL")
    engine = create_engine(supabase_url)
    
    with Session(engine) as session:
        # 1. Create Experiments
        exp1_id = f"exp_{str(uuid.uuid4())[:8]}"
        exp2_id = f"exp_{str(uuid.uuid4())[:8]}"
        
        e1 = DBExperimentRegistry(
            id=exp1_id,
            start_time=datetime.now() - timedelta(days=2),
            end_time=datetime.now() - timedelta(days=2) + timedelta(hours=1),
            dataset_version="v1.0",
            feature_version="v1.0",
            feature_families_tested='["statistics"]',
            metrics_summary={"accuracy": 0.65}
        )
        e2 = DBExperimentRegistry(
            id=exp2_id,
            start_time=datetime.now() - timedelta(hours=5),
            end_time=datetime.now() - timedelta(hours=4),
            dataset_version="v2.0",
            feature_version="v1.5",
            feature_families_tested='["statistics", "astronomy", "environment"]',
            metrics_summary={"accuracy": 0.78}
        )
        session.add_all([e1, e2])
        
        # 2. Create Models
        m1_id = f"mod_{str(uuid.uuid4())[:8]}"
        m2_id = f"mod_{str(uuid.uuid4())[:8]}"
        
        m1 = DBModelRegistry(
            id=m1_id,
            experiment_id=exp1_id,
            algorithm="LogisticRegression",
            train_start_year=2010, train_end_year=2020,
            test_start_year=2021, test_end_year=2023,
            parameters={"C": 1.0, "penalty": "l2"},
            random_seed=42,
            performance_metrics={"accuracy": 0.654, "log_loss": 0.68, "roc_auc": 0.62},
            calibration_metrics={"brier_score": 0.22},
            execution_time_seconds=145.2,
            is_champion=False
        )
        
        m2 = DBModelRegistry(
            id=m2_id,
            experiment_id=exp2_id,
            algorithm="XGBoost",
            train_start_year=2010, train_end_year=2023,
            test_start_year=2024, test_end_year=2025,
            parameters={"max_depth": 6, "learning_rate": 0.01, "n_estimators": 500},
            random_seed=42,
            performance_metrics={"accuracy": 0.785, "log_loss": 0.49, "roc_auc": 0.81},
            calibration_metrics={"brier_score": 0.15},
            execution_time_seconds=1845.6,
            is_champion=True
        )
        session.add_all([m1, m2])
        e1.winning_model_id = m1_id
        e2.winning_model_id = m2_id
        
        # 3. Create Features
        features = [
            ("win_rate_last_5", 0.18, 0.45, "cricket", "Team win rate in last 5 matches"),
            ("venue_win_rate", 0.12, 0.38, "cricket", "Team historic win rate at venue"),
            ("toss_winner_is_team_a", 0.08, 0.22, "cricket", "Did team A win the toss"),
            ("moon_phase_illumination", 0.04, 0.15, "astronomy", "Lunar illumination %"),
            ("temperature_celsius", 0.03, 0.11, "environment", "Match day temp"),
            ("head_to_head_ratio", 0.15, 0.41, "cricket", "H2H win ratio"),
            ("player_form_index_team_a", 0.11, 0.35, "cricket", "Aggregated top order form")
        ]
        
        for name, imp, corr, dom, desc in features:
            f = DBFeatureRegistry(
                id=f"feat_{name}",
                feature_name=name,
                domain=dom,
                description=desc,
                baseline_importance=imp,
                correlation_score=corr,
                usefulness_flag=True
            )
            # Try merge since it's unique
            session.merge(f)
            
        # 4. Create Predictions (Live Monitor)
        real_events = session.execute(__import__("sqlalchemy").text("SELECT id FROM events LIMIT 10")).fetchall()
        real_match_ids = [r[0] for r in real_events]
        
        teams = ["ind", "aus", "eng", "rsa"]
        for i, match_id in enumerate(real_match_ids):
            p = DBPredictionStore(
                id=f"pred_{str(uuid.uuid4())[:8]}",
                match_id=match_id,
                model_id=m2_id,
                prediction_timestamp=datetime.now() - timedelta(minutes=i*15),
                predicted_winner_id=random.choice(teams),
                probability=random.uniform(0.55, 0.89),
                confidence=random.uniform(0.6, 0.95),
                dataset_version="v2.0",
                feature_version="v1.5",
                actual_winner_id=None,
                is_correct=None,
                top_driving_features={"win_rate_last_5": 0.2, "head_to_head_ratio": 0.15}
            )
            session.add(p)
            
        session.commit()
        print("Mock ML Data successfully injected into Supabase!")

if __name__ == "__main__":
    main()
