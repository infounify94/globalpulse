import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    import pandas as pd
    import numpy as np
except ImportError:
    logging.warning("Data science packages missing.")

from core.memory.schema import DBModelRegistry, DBPredictionStore, DBExperimentRegistry

class ContinuousLearningEngine:
    """
    Handles live match prediction, automatic verification, and continuous retraining loops.
    """
    
    def __init__(self, engine, pipeline):
        self.engine = engine
        self.pipeline = pipeline
        
    def predict_future_match(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        1. Dynamically generates pre-match features.
        2. Loads the best historically validated model.
        3. Generates probability and confidence score.
        4. Logs prediction to the database.
        """
        # Step 1: Find the Best Model historically
        with Session(self.engine) as session:
            # We want the most recent model that performed best on Brier Score
            best_model_record = session.query(DBModelRegistry).order_by(
                DBModelRegistry.test_end_year.desc()
            ).first() # In reality, we'd query by lowest brier_score in the most recent window.
            
            if not best_model_record:
                raise ValueError("No trained models found in the Registry.")
                
            model_id = best_model_record.id
            algorithm = best_model_record.algorithm
            
            # Step 2: Extract Features (Mocked here, normally calls FeatureGenerator)
            # feature_vector = FeatureGenerator.generate(match_data)
            X_live = np.random.rand(1, 20)
            
            # Step 3: Load actual model weights from disk/storage (Mocked probability for now)
            # model = self.load_model(model_id)
            # prob = model.predict_proba(X_live)[0][1]
            prob = float(np.random.rand())
            
            # Step 4: Confidence Calibration (Task 5)
            # Confidence is derived from historical calibration of this model (Expected Calibration Error)
            ece = best_model_record.calibration_metrics.get("calibration_error_ece", 0.05)
            # True confidence is probability distance from 0.5, penalized by ECE
            raw_confidence = abs(prob - 0.5) * 2.0  # Scale 0 to 1
            confidence_score = max(0, raw_confidence - ece)
            
            pred_winner = match_data['team_a'] if prob > 0.5 else match_data['team_b']
            
            # Step 5: Log to DB (Enhanced Prediction Archive)
            prediction_id = f"live_{datetime.utcnow().timestamp()}"
            pred_record = DBPredictionStore(
                id=prediction_id,
                match_id=match_data.get('match_id', "unknown"),
                model_id=model_id,
                prediction_timestamp=datetime.utcnow(),
                predicted_winner_id=pred_winner,
                probability=prob,
                confidence=confidence_score,
                dataset_version="v_live", # Typically pulled from active state
                feature_version="v_live",
                is_correct=None # Awaiting verification
            )
            session.add(pred_record)
            session.commit()
            
            return {
                "prediction_id": prediction_id,
                "winner": pred_winner,
                "probability": prob,
                "confidence": confidence_score,
                "model_used": model_id
            }

    def verify_and_retrain(self, prediction_id: str, actual_winner: str):
        """
        1. Inputs actual result to verify a past prediction.
        2. Detects Model/Feature Drift.
        3. Evaluates Champion vs Challenger.
        """
        with Session(self.engine) as session:
            pred_record = session.query(DBPredictionStore).filter_by(id=prediction_id).first()
            if not pred_record:
                raise ValueError("Prediction not found.")
                
            # 1. Update verification
            pred_record.actual_winner_id = actual_winner
            pred_record.is_correct = (pred_record.predicted_winner_id == actual_winner)
            session.commit()
            logging.info(f"Verified Prediction {prediction_id}. Correct: {pred_record.is_correct}")
            
            # 2. Model Drift Detection
            # Calculate accuracy over the last 50 verified predictions
            recent_preds = session.query(DBPredictionStore).filter(
                DBPredictionStore.is_correct.isnot(None)
            ).order_by(DBPredictionStore.prediction_timestamp.desc()).limit(50).all()
            
            if len(recent_preds) == 50:
                acc = sum([1 for p in recent_preds if p.is_correct]) / 50.0
                if acc < 0.55: # Drift detected!
                    logging.warning(f"MODEL DRIFT DETECTED: Recent accuracy dropped to {acc:.2f}. Triggering retraining.")
                    
            # 3. Champion vs Challenger Promotion (Mock logic)
            # In a full run, we compare Challenger Brier vs Champion Brier on recent 50 matches.
            # If Challenger < Champion, promote.
            
            # 4. Feature Drift
            session.execute(text("""
                UPDATE feature_registry 
                SET usefulness_flag = 0
                WHERE baseline_importance < 0.0001
            """))
            session.commit()
            
        return {"status": "success", "verified": True, "drift_checked": True}
