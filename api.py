from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, uvicorn, logging, joblib
from sqlalchemy.orm import Session
from core.memory.schema import get_engine, create_tables, DBPredictionLineage
from core.engine.continuous_learning import ContinuousLearningEngine
from core.engine.ancient_engine import AncientPredictionEngine

CRICAPI_KEY = os.environ.get("CRICAPI_KEY", "bd50097b-082d-4d9d-88aa-b0e47a1bb9cc")
ancient_engine = AncientPredictionEngine()

app = FastAPI(title="GlobalPulse Prediction API", version="4.0")

# Mount frontend directory so user can access it via localhost:8000/frontend/index.html
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
def root():
    return RedirectResponse(url="/frontend/index.html")

# Add CORS so Cloudflare Pages frontend can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to your Cloudflare Pages URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup DB
db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
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
        return {"status": "ready", "database": db_url.split(":")[0]}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {e}")

@app.get("/version")
def get_version():
    return {"version": "1.0.0", "status": "production"}

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
                "train_years": f"{m.train_start_year}-{m.train_end_year}",
                "test_years": f"{m.test_start_year}-{m.test_end_year}",
                "is_champion": getattr(m, 'is_champion', False),
                "artifact_ready": artifact_exists,
                "accuracy": metrics.get("accuracy", None),
                "brier_score": metrics.get("brier_score", None),
                "log_loss": metrics.get("log_loss", None),
                "artifact_path": m.model_artifact_path,
                "feature_importance": getattr(m, 'feature_importance', {}),
                "season_metrics": getattr(m, 'season_metrics', {}),
                "statistical_significance": getattr(m, 'statistical_significance', {}),
            })
            
        # Optional: return top 10 models for leaderboard
        result = sorted(result, key=lambda x: x["accuracy"] or 0, reverse=True)[:10]
        
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

# ── Ancient Prediction Endpoints ──────────────────────────────────────────

def _fetch_cricapi_squad(match_id: str) -> dict:
    """Fetch playing XI from CricAPI for a given match ID."""
    try:
        import requests
        r = requests.get(
            f"https://api.cricapi.com/v1/match_info?apikey={CRICAPI_KEY}&id={match_id}",
            timeout=8
        )
        data = r.json().get("data", {})
        players = data.get("players", {})
        teams = data.get("teams", [])
        team_a_players = players.get(teams[0], []) if teams else []
        team_b_players = players.get(teams[1], []) if len(teams) > 1 else []
        return {"team_a": team_a_players, "team_b": team_b_players, "raw": data}
    except Exception as e:
        logging.warning(f"CricAPI squad fetch failed: {e}")
        return {"team_a": [], "team_b": []}


def _fetch_current_matches_with_squads() -> list:
    """Fetch live/recent matches from CricAPI that have squad data."""
    try:
        import requests
        r = requests.get(
            f"https://api.cricapi.com/v1/currentMatches?apikey={CRICAPI_KEY}&offset=0",
            timeout=8
        )
        matches = r.json().get("data", [])
        result = []
        for m in matches:
            if m.get("teams") and len(m["teams"]) == 2:
                result.append({
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "teams": m.get("teams"),
                    "venue": m.get("venue", "Unknown"),
                    "date": m.get("date"),
                    "matchType": m.get("matchType", "t20"),
                    "status": m.get("status", ""),
                    "score": m.get("score", []),
                    "teamInfo": m.get("teamInfo", []),
                })
        return result
    except Exception as e:
        logging.warning(f"CricAPI current matches fetch failed: {e}")
        return []


@app.get("/api/ancient/predict")
def ancient_predict(
    team_a: str = Query(...),
    team_b: str = Query(...),
    date: str = Query(None),
    venue: str = Query(""),
    cricapi_id: str = Query(None),
    players_a: str = Query(""),   # comma-separated player names
    players_b: str = Query(""),
):
    """
    Runs all 4 ancient prediction systems (Jyotish, Babylonian, Numerology, Pancha Bhuta).
    Optionally fetches playing XI from CricAPI if cricapi_id is provided.
    """
    from datetime import date as date_type, datetime as dt_type

    # Parse date
    try:
        match_date = dt_type.strptime(date, "%Y-%m-%d").date() if date else date_type.today()
    except Exception:
        match_date = date_type.today()

    # Parse manually entered players
    p_a = [p.strip() for p in players_a.split(",") if p.strip()] if players_a else []
    p_b = [p.strip() for p in players_b.split(",") if p.strip()] if players_b else []

    # Auto-fetch from CricAPI if an ID is given and we don't have players
    squad_source = "manual"
    if cricapi_id and (not p_a or not p_b):
        squad = _fetch_cricapi_squad(cricapi_id)
        if squad.get("team_a"):
            p_a = squad["team_a"]
            squad_source = "CricAPI"
        if squad.get("team_b"):
            p_b = squad["team_b"]

    try:
        result = ancient_engine.predict(
            team_a=team_a, team_b=team_b,
            match_date=match_date, venue=venue,
            players_a=p_a, players_b=p_b
        )
        result["squad_source"] = squad_source
        result["players_a"] = p_a
        result["players_b"] = p_b
        return result
    except Exception as e:
        logging.error(f"Ancient prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ancient/live")
def ancient_live_matches():
    """
    Fetches all current cricket matches from CricAPI and runs ancient predictions on each.
    This powers the Ancient Engine page with real live data.
    """
    from datetime import date as date_type
    matches = _fetch_current_matches_with_squads()
    results = []
    for m in matches[:10]:  # limit to 10 to stay within API quota
        teams = m.get("teams", ["Team A", "Team B"])
        team_a = teams[0] if teams else "Team A"
        team_b = teams[1] if len(teams) > 1 else "Team B"

        try:
            match_date_str = m.get("date", date_type.today().isoformat())
            from datetime import datetime as dt_type
            match_date = dt_type.strptime(match_date_str, "%Y-%m-%d").date()
        except Exception:
            match_date = date_type.today()

        try:
            prediction = ancient_engine.predict(
                team_a=team_a, team_b=team_b,
                match_date=match_date,
                venue=m.get("venue", ""),
                players_a=[], players_b=[]
            )
            results.append({
                "match": m,
                "ancient_prediction": prediction
            })
        except Exception as e:
            logging.warning(f"Could not predict {team_a} vs {team_b}: {e}")

    return {"count": len(results), "predictions": results}

@app.get("/api/shadow_predictions")
def get_shadow_predictions():
    from sqlalchemy.orm import Session
    from core.memory.schema import DBShadowPrediction
    
    with Session(engine) as session:
        preds = session.query(DBShadowPrediction).order_by(DBShadowPrediction.date.desc()).limit(100).all()
        return [{
            "match_id": p.match_id,
            "date": p.date.isoformat() if p.date else None,
            "team_a": p.team_a,
            "team_b": p.team_b,
            "predicted_winner": p.predicted_winner,
            "probability": p.probability,
            "confidence_bucket": p.confidence_bucket,
            "top_shap_features": p.top_shap_features,
            "actual_winner": p.actual_winner,
            "verified_time": p.verified_time.isoformat() if p.verified_time else None
        } for p in preds]

@app.get("/api/shadow_metrics")
def get_shadow_metrics():
    from sqlalchemy.orm import Session
    from core.memory.schema import DBShadowMetric
    
    with Session(engine) as session:
        metric = session.query(DBShadowMetric).order_by(DBShadowMetric.timestamp.desc()).first()
        if not metric:
            return {}
        return {
            "overall_accuracy": metric.overall_accuracy,
            "rolling_50_accuracy": metric.rolling_50_accuracy,
            "rolling_100_accuracy": metric.rolling_100_accuracy,
            "brier_score": metric.brier_score,
            "log_loss": metric.log_loss,
            "roi": metric.roi,
            "timestamp": metric.timestamp.isoformat() if metric.timestamp else None
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
