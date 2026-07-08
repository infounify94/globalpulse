import os
import uuid
import logging
import json
import subprocess
from datetime import datetime
from typing import List, Dict, Any

try:
    import pandas as pd
    import numpy as np
    import joblib
    from sklearn.calibration import CalibratedClassifierCV
except ImportError:
    logging.warning("scikit-learn, joblib, or pandas missing. Pipeline will not execute.")

from sqlalchemy.orm import Session
from sqlalchemy import text
from core.memory.schema import (
    get_engine, DBExperimentRegistry, DBModelRegistry, DBPredictionStore,
    DBFeatureStatistics, DBFeatureAstronomy, DBFeatureEnvironment, DBPredictionLineage
)
from core.engine.metrics import ModelMetrics

MODEL_STORE_DIR = "model_store"

FAMILY_COLUMN_PREFIXES = {
    "statistics":  ["stat_"],
    "astronomy":   ["astro_"],
    "environment": ["env_"],
    "temporal":    ["temporal_"],
}


def _get_git_hash() -> str:
    """Returns the current git commit hash for lineage tracking."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


class TrainingPipeline:
    def __init__(self, engine, dataset_dir="datasets"):
        self.engine = engine
        self.dataset_dir = dataset_dir
        os.makedirs(MODEL_STORE_DIR, exist_ok=True)

    def _build_feature_matrix(self, df: pd.DataFrame, feature_family: str) -> np.ndarray:
        """
        Constructs a real feature matrix from stored JSON feature columns.
        This replaces the np.random.rand() stub with actual data.
        """
        # Determine which feature table columns to include
        families = [f.strip() for f in feature_family.split(",")]
        all_columns = []

        for row_idx, row in df.iterrows():
            row_features = {}

            for fam in families:
                # Map family name to the column name generated in dataset_generator.py
                col_map = {
                    "statistics": "stat_features",
                    "astronomy": "astro_features",
                    "environment": "env_features"
                }
                col = col_map.get(fam, f"{fam}_features")
                
                if col in row and row[col] is not None:
                    # Some pandas versions handle NaNs for missing objects, check for that
                    if isinstance(row[col], float) and pd.isna(row[col]):
                        continue
                        
                    if row[col] not in ("", "null"):
                        try:
                            feat_dict = json.loads(row[col]) if isinstance(row[col], str) else row[col]
                            if isinstance(feat_dict, dict):
                                row_features.update(feat_dict)
                        except (json.JSONDecodeError, TypeError):
                            pass

            all_columns.append(row_features)

        if not all_columns or not any(all_columns):
            # Fallback: if features aren't in parquet, try to load from DB directly
            logging.warning(
                "Feature columns not found in parquet. "
                "Run 'python etl_run.py --features' first to populate feature tables."
            )
            # Minimum viable: return zeros so pipeline doesn't crash
            n_rows = len(df)
            return np.zeros((n_rows, 10))

        # Convert list of dicts to DataFrame, fill missing values with column median
        feat_df = pd.DataFrame(all_columns).fillna(0.0)
        # Keep only numeric columns
        feat_df = feat_df.select_dtypes(include=[np.number])

        if feat_df.empty:
            return np.zeros((len(df), 10))

        return feat_df.values

    def _extract_xy(self, df: pd.DataFrame, feature_family: str):
        """Extracts real feature matrix (X) and target labels (y)."""
        X = self._build_feature_matrix(df, feature_family)
        y = (df['outcome'] == df['team_a_id']).astype(int).values
        return X, y

    def run_experiment(self,
                       experiment_id: str,
                       train_files: List[str],
                       test_files: List[str],
                       trainers: List[Any],
                       feature_families: List[str],
                       dataset_version: str = "v1",
                       feature_version: str = "v1",
                       use_optuna: bool = False,
                       optuna_trials: int = 30):

        start_time = datetime.utcnow()
        git_hash = _get_git_hash()
        logging.info(f"Starting Experiment: {experiment_id} | dataset={dataset_version} | commit={git_hash}")

        with Session(self.engine) as session:
            experiment = DBExperimentRegistry(
                id=experiment_id,
                start_time=start_time,
                dataset_version=dataset_version,
                feature_version=feature_version,
                feature_families_tested=json.dumps(feature_families)
            )
            session.add(experiment)
            session.commit()

            all_results = []

            for train_file, test_file in zip(train_files, test_files):
                train_path = os.path.join(self.dataset_dir, train_file)
                test_path = os.path.join(self.dataset_dir, test_file)

                if not os.path.exists(train_path) or not os.path.exists(test_path):
                    logging.warning(f"Dataset files not found: {train_path} / {test_path}")
                    continue

                train_df = pd.read_parquet(train_path)
                test_df = pd.read_parquet(test_path)

                if len(train_df) == 0 or len(test_df) == 0:
                    logging.warning("Empty dataset — skipping split.")
                    continue

                try:
                    tr_start, tr_end = [int(x) for x in train_file.replace('.parquet', '').split('_')[1:3]]
                    te_start, te_end = [int(x) for x in test_file.replace('.parquet', '').split('_')[1:3]]
                except Exception:
                    tr_start, tr_end, te_start, te_end = 2008, 2018, 2019, 2019

                for family in feature_families:
                    X_train, y_train = self._extract_xy(train_df, family)
                    X_test, y_test = self._extract_xy(test_df, family)

                    # Ensure X has enough features for calibration CV
                    if X_train.shape[1] == 0:
                        logging.warning(f"Zero features for family '{family}'. Skipping.")
                        continue

                    for trainer in trainers:
                        model_id = f"{experiment_id}_{trainer.algorithm_name}_{family.replace(',','_')}_{te_start}"
                        logging.info(f"Training {model_id}...")
                        
                        best_params = None
                        if use_optuna:
                            from core.engine.optuna_optimizer import OptunaOptimizer
                            optimizer = OptunaOptimizer(trainer.algorithm_name, n_trials=optuna_trials)
                            try:
                                best_params = optimizer.optimize(X_train, y_train)
                                logging.info(f"Optuna found best params: {best_params}")
                            except BaseException as e:
                                logging.warning(f"Optuna failed: {e}. Falling back to defaults.")

                        train_start_ts = datetime.utcnow()
                        trainer.train(X_train, y_train, params=best_params)

                        # Calibration Layer
                        calibrated_cv = CalibratedClassifierCV(trainer.get_model(), method='isotonic', cv=3)
                        calibrated_cv.fit(X_train, y_train)

                        exec_time = (datetime.utcnow() - train_start_ts).total_seconds()

                        y_pred = calibrated_cv.predict(X_test)
                        y_prob = calibrated_cv.predict_proba(X_test)[:, 1]

                        metrics = ModelMetrics.evaluate(y_test, y_pred, y_prob)

                        # ── GAP-01 FIX: Save model weights to disk ──────────────
                        artifact_path = os.path.join(MODEL_STORE_DIR, f"{model_id}.joblib")
                        joblib.dump(calibrated_cv, artifact_path)
                        logging.info(f"Model artifact saved: {artifact_path}")

                        # Save Model to Registry
                        model_record = DBModelRegistry(
                            id=model_id,
                            experiment_id=experiment_id,
                            algorithm=trainer.algorithm_name,
                            train_start_year=tr_start, train_end_year=tr_end,
                            test_start_year=te_start, test_end_year=te_end,
                            parameters=trainer.get_default_parameters(),
                            random_seed=trainer.random_seed,
                            performance_metrics=metrics,
                            calibration_metrics={"calibration_error_ece": metrics.get("calibration_error_ece", 0)},
                            execution_time_seconds=exec_time,
                            model_artifact_path=artifact_path,
                            is_champion=False
                        )
                        session.add(model_record)

                        preds = []
                        lineages = []
                        # Save Predictions + Lineage
                        for i, match_id in enumerate(test_df['id'].values):
                            prob = float(y_prob[i])
                            pred_winner = (
                                test_df.iloc[i]['team_a_id'] if prob > 0.5
                                else test_df.iloc[i]['team_b_id']
                            )
                            actual_winner = test_df.iloc[i]['outcome']
                            pred_id = str(uuid.uuid4())

                            pred_record = DBPredictionStore(
                                id=pred_id,
                                match_id=str(match_id),
                                model_id=model_id,
                                prediction_timestamp=datetime.utcnow(),
                                predicted_winner_id=str(pred_winner),
                                probability=prob,
                                confidence=max(0.0, abs(prob - 0.5) * 2.0),
                                dataset_version=dataset_version,
                                feature_version=feature_version,
                                actual_winner_id=str(actual_winner),
                                is_correct=(pred_winner == actual_winner)
                            )
                            preds.append(pred_record)

                            # Data Lineage record
                            lineage = DBPredictionLineage(
                                id=str(uuid.uuid4()),
                                prediction_id=pred_id,
                                model_id=model_id,
                                model_artifact_path=artifact_path,
                                dataset_version=dataset_version,
                                feature_version=feature_version,
                                hyperparameters=trainer.get_default_parameters(),
                                feature_families_used=family,
                                connector_name="cricsheet",
                                connector_version="1.0",
                                git_commit_hash=git_hash,
                                training_timestamp=train_start_ts,
                                prediction_timestamp=datetime.utcnow()
                            )
                            lineages.append(lineage)

                        session.add_all(preds)
                        session.flush()
                        session.add_all(lineages)
                        session.commit()
                        all_results.append((model_id, metrics.get("brier_score", 1.0)))

            # Determine overall winner by lowest Brier Score
            if all_results:
                winning_model_id = sorted(all_results, key=lambda x: x[1])[0][0]
                experiment.winning_model_id = winning_model_id
                experiment.end_time = datetime.utcnow()

                # Mark winner as Champion
                champ = session.query(DBModelRegistry).filter_by(id=winning_model_id).first()
                if champ:
                    champ.is_champion = True

                session.commit()
                logging.info(f"Experiment {experiment_id} complete. Champion: {winning_model_id}")
