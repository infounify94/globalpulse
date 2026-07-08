from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, uvicorn, logging, joblib
from sqlalchemy.orm import Session
from core.memory.schema import get_engine, create_tables, DBPredictionLineage
from core.engine.continuous_learning import ContinuousLearningEngine

app = FastAPI(title="GlobalPulse Prediction API", version="4.0")

# Add CORS so Cloudflare Pages frontend can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to your Cloudflare Pages URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/api/matches/upcoming")
def get_upcoming_matches(gender: str = None, match_type: str = None, venue: str = None):
    """
    Returns a realistic schedule of future matches.
    Automatically runs the AI prediction engine on each match before returning!
    """
    from datetime import datetime, timedelta
    import uuid
    
    today = datetime.utcnow().date()
    
    # Mock realistic schedule
    all_matches = [
        {"team_a": "India", "team_b": "Australia", "venue": "Melbourne Cricket Ground", "match_type": "T20I", "gender": "male", "date": (today + timedelta(days=1)).isoformat()},
        {"team_a": "England", "team_b": "Pakistan", "venue": "Lord's", "match_type": "ODI", "gender": "male", "date": (today + timedelta(days=2)).isoformat()},
        {"team_a": "South Africa", "team_b": "New Zealand", "venue": "Wanderers Stadium", "match_type": "T20I", "gender": "male", "date": (today + timedelta(days=3)).isoformat()},
        {"team_a": "India", "team_b": "England", "venue": "Wankhede Stadium", "match_type": "T20I", "gender": "female", "date": (today + timedelta(days=4)).isoformat()},
        {"team_a": "Australia", "team_b": "New Zealand", "venue": "Sydney Cricket Ground", "match_type": "ODI", "gender": "female", "date": (today + timedelta(days=5)).isoformat()},
        {"team_a": "Sri Lanka", "team_b": "Bangladesh", "venue": "R.Premadasa Stadium", "match_type": "T20I", "gender": "male", "date": (today + timedelta(days=6)).isoformat()},
        {"team_a": "West Indies", "team_b": "England", "venue": "Kensington Oval", "match_type": "T20I", "gender": "male", "date": (today + timedelta(days=7)).isoformat()},
        {"team_a": "India", "team_b": "Australia", "venue": "Narendra Modi Stadium", "match_type": "Test", "gender": "male", "date": (today + timedelta(days=10)).isoformat()},
        {"team_a": "South Africa", "team_b": "England", "venue": "Newlands", "match_type": "T20I", "gender": "female", "date": (today + timedelta(days=11)).isoformat()},
        {"team_a": "Pakistan", "team_b": "New Zealand", "venue": "Gaddafi Stadium", "match_type": "ODI", "gender": "male", "date": (today + timedelta(days=12)).isoformat()},
    ]
    
    # Apply Filters
    filtered = all_matches
    if gender and gender.lower() != "all":
        filtered = [m for m in filtered if m['gender'].lower() == gender.lower()]
    if match_type and match_type.lower() != "all":
        filtered = [m for m in filtered if m['match_type'].lower() == match_type.lower()]
    if venue:
        filtered = [m for m in filtered if venue.lower() in m['venue'].lower()]
        
    # Autonomous Prediction!
    for match in filtered:
        match['match_id'] = f"live_mock_{uuid.uuid4().hex[:8]}"
        try:
            prediction = learning_engine.predict_future_match(match)
            match['prediction'] = prediction
        except Exception as e:
            logging.error(f"Failed to auto-predict {match['match_id']}: {e}")
            match['prediction'] = {"error": str(e)}
            
    return {"matches": filtered}

@app.get("/api/models")
def get_all_models():
    """Returns all registered trained models with their details for the frontend AI Analytics page."""
    import os
    from core.memory.schema import DBModelRegistry
    with Session(engine) as session:
        models = session.query(DBModelRegistry).all()
        result = []
        for m in models:
            artifact_exists = os.path.exists(m.model_artifact_path) if m.model_artifact_path else False
            metrics = m.performance_metrics or {}
            result.append({
                "id": m.id,
                "algorithm": m.algorithm,
                "feature_family": getattr(m, 'feature_families', m.algorithm),
                "train_years": f"{m.train_start_year}–{m.train_end_year}",
                "test_year": m.test_end_year,
                "is_champion": getattr(m, 'is_champion', False),
                "artifact_ready": artifact_exists,
                "accuracy": metrics.get("accuracy", None),
                "brier_score": metrics.get("brier_score", None),
                "log_loss": metrics.get("log_loss", None),
                "artifact_path": m.model_artifact_path,
            })
    return {"models": result}



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
