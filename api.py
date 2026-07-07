from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os, uvicorn, logging, joblib
from sqlalchemy.orm import Session
from core.memory.schema import get_engine, create_tables, DBPredictionLineage
from core.engine.continuous_learning import ContinuousLearningEngine

app = FastAPI(title="GlobalPulse Prediction API", version="4.0")

# Setup DB
db_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
engine = get_engine(db_url)
create_tables(engine)
learning_engine = ContinuousLearningEngine(engine, pipeline=None)

class MatchRequest(BaseModel):
    match_id: str
    sport: str
    match_type: str
    date: str
    venue: str
    team_a: str
    team_b: str
    toss: str = None

class VerificationRequest(BaseModel):
    prediction_id: str
    actual_winner: str

@app.get("/health")
def health_check():
    """Kubernetes/Docker health probe — returns 200 if API is alive."""
    return {"status": "ok", "timestamp": __import__('datetime').datetime.utcnow().isoformat()}

@app.get("/ready")
def readiness_check():
    """Returns 200 only if database connection is healthy."""
    try:
        with engine.connect() as conn:
            conn.execute(__import__('sqlalchemy').text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {e}")

@app.post("/predict")
def predict_match(request: MatchRequest):
    """
    Predicts the outcome of a future match.
    Loads best model, calculates confidence, and stores prediction for future verification.
    """
    try:
        result = learning_engine.predict_future_match(request.dict())
        return result
    except Exception as e:
        logging.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify")
def verify_prediction(request: VerificationRequest):
    """
    Verifies a past prediction, updates feature usefulness, and triggers continuous retraining.
    """
    try:
        result = learning_engine.verify_and_retrain(request.prediction_id, request.actual_winner)
        return result
    except Exception as e:
        logging.error(f"Verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
