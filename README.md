# GlobalPulse — Scientific Prediction Research Platform

> A production-grade, domain-agnostic ML prediction engine with strict chronological Walk-Forward validation, Champion/Challenger model governance, and a full MLOps lifecycle.

---

## Quick Start (Local Development)

```bash
# 1. Clone and enter the project
cd d:\PredictionEngine

# 2. Create .env from template (already created — edit DB password)
copy .env .env.local

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download + import all historical cricket data (~300MB, one-time)
python etl_run.py --all

# 5. Check database status
python etl_run.py --status

# 6. Start the Prediction API
uvicorn api:app --reload --port 8000

# 7. Start the Research Dashboard (separate terminal)
streamlit run dashboard/app.py
```

Access:
- **Dashboard**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Data Layer                                                │
│  Cricsheet (free) → Parser → Loader → SQLite/PostgreSQL    │
│  Open-Meteo (free) → WeatherConnector → feature_environment│
│  CricAPI (free) → LiveConnector → upcoming matches         │
└─────────────────────────┬──────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────┐
│  Feature Engine                                            │
│  CricketStatsGenerator  (strict temporal, no leakage)      │
│  AstronomyGenerator     (Swiss Ephemeris)                  │
│  EnvironmentGenerator   (Open-Meteo)                       │
└─────────────────────────┬──────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────┐
│  ML Pipeline                                               │
│  Walk-Forward Validation (no random splits ever)           │
│  XGBoost / LightGBM / LogisticRegression / RandomForest    │
│  Optuna Hyperparameter Optimization                        │
│  CalibratedClassifierCV (probability calibration)          │
│  Champion vs Challenger promotion (statistical)            │
│  Drift Detection (accuracy + feature distribution)         │
│  model_store/*.joblib (persistent model weights)           │
└─────────────────────────┬──────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────┐
│  API Layer (FastAPI)                                       │
│  POST /predict   — Real-time match prediction              │
│  POST /verify    — Submit actual match result              │
│  GET  /health    — Health check                            │
│  GET  /ready     — Readiness check                         │
│  GET  /lineage/{id} — Full prediction audit trail          │
└─────────────────────────┬──────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────┐
│  Dashboard (Streamlit — 12 pages)                          │
│  Dashboard / Upcoming / Predictions / History              │
│  Model Performance / Features / Data Health                │
│  Experiments / Retraining / Settings / Logs / Lineage      │
└────────────────────────────────────────────────────────────┘
```

---

## Free APIs Used

| Service | Purpose | Key Required |
|---|---|---|
| Cricsheet | Historical match data | No — auto-downloaded |
| Open-Meteo | Weather data | No — no key needed |
| Open-Elevation | Venue altitude | No — no key needed |
| Swiss Ephemeris | Astronomy features | No — library |
| CricAPI | Live schedules/results | Yes — get free at cricapi.com |

---

## ETL Commands

```bash
python etl_run.py --download   # Download Cricsheet data
python etl_run.py --import     # Parse + insert into database
python etl_run.py --features   # Generate all features
python etl_run.py --all        # Full pipeline
python etl_run.py --status     # Show database row counts
```

---

## Production Deployment (Cloudflare Tunnel)

See [docs/deploy/cloudflare.md](docs/deploy/cloudflare.md) for full instructions.

```bash
# Start all services
docker-compose up --build

# Expose via Cloudflare Tunnel (free HTTPS)
cloudflared tunnel --url http://localhost:8501
```

---

## Adding a New Domain (Plugin Framework)

Implement `plugins/base_plugin.py:BasePlugin` — just 5 methods:
1. `get_feature_generator()` — domain-specific feature logic
2. `get_connector()` — data source for this domain
3. `parse_event()` — raw data → BaseEvent
4. `target_variable()` — what are we predicting?
5. `validation_rules()` — what is valid data?

See `plugins/cricket/` for a reference implementation.

---

## Phase Completion

| Phase | Description | Status |
|---|---|---|
| 1 | Domain-agnostic schema + base engine | ✅ Complete |
| 2 | Walk-Forward Validation | ✅ Complete |
| 3 | Feature families (stats, astro, env) | ✅ Complete |
| 4 | Scientific benchmarking | ✅ Complete |
| 5 | Research dashboards | ✅ Complete |
| 6 | Autonomous MLOps + Optuna | ✅ Complete |
| 7 | Live data connectors + real ETL | ✅ Complete |
| 8 | Production UI (12 pages) | ✅ Complete |
| 9 | Hosting + Cloudflare deployment | ✅ Complete |
| 11 | Universal plugin framework | ✅ Complete |
| 12 | Data lineage + audit system | ✅ Complete |
