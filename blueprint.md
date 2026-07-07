# GlobalPulse — Complete Project Blueprint
> **Last Updated:** July 2026 | **Version:** 1.0

---

## What Is GlobalPulse?

GlobalPulse is a **scientific match outcome prediction engine**, initially built for cricket. It uses machine learning trained on 15+ years of historical data combined with statistical, astronomical, and environmental features.

**Core Principle:** Never use random data splits. Always train on past data, test on unseen future data (Walk-Forward Validation).

---

## How It Works — Complete Flow

```
[Step 1] Data Collection
  Cricsheet (free) → 22,228 historical matches (ODI, T20, Test, IPL)
  CricAPI (free key) → Live upcoming matches + completed results

[Step 2] Parsing & Storage
  JSON files → CricsheetParser → PostgreSQL/SQLite database
  Tables: events, cricket_match_metadata, innings, deliveries, teams, venues

[Step 3] Feature Generation (3 families)
  CricketStatsGenerator → batting avg, win rates, head-to-head, venue stats
  AstronomyGenerator   → moon phase, nakshatra, tithi, planet positions
  WeatherConnector     → temperature, wind, rain, humidity, altitude

[Step 4] Walk-Forward ML Training
  2008-2018 train → 2019 test
  2008-2019 train → 2020 test
  2008-2020 train → 2021 test  ... and so on
  Algorithms: XGBoost, LightGBM, RandomForest, LogisticRegression, GradientBoosting, ExtraTrees
  Calibration: CalibratedClassifierCV (isotonic) for accurate probabilities

[Step 5] Champion vs Challenger Governance
  New model trains as Challenger → Walk-forward validation
  Statistical test: is Challenger better than Champion?
  Yes → Promote (Champion replaced)
  No  → Reject (old Champion stays)

[Step 6] Predictions Stored Forever
  Every prediction: match_id, model_id, probability, confidence,
  dataset_version, feature_version, git_commit_hash, actual_result

[Step 7] Verification Loop (APScheduler)
  After each match → fetch result from CricAPI
  → mark prediction correct/wrong
  → update drift metrics
  → trigger retraining if accuracy drops below threshold

[Step 8] Dashboard + API
  12-page Streamlit research dashboard
  FastAPI REST API for external prediction requests
```

---

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.12 |
| Database (local dev) | SQLite | Built-in |
| Database (production) | Supabase PostgreSQL | Free tier |
| ML Framework | Scikit-learn, XGBoost, LightGBM | Latest |
| Hyperparameter Tuning | Optuna | 3.x |
| Probability Calibration | CalibratedClassifierCV | Sklearn |
| Model Explainability | SHAP | Latest |
| API | FastAPI + Uvicorn | Latest |
| Dashboard | Streamlit | Latest |
| Scheduler | APScheduler | 3.x |
| Deployment | Cloudflare Tunnel | Free |
| Environment | python-dotenv | Latest |

---

## API Keys & Services

### 1. CricAPI — Live Cricket Data
- **URL:** https://cricapi.com
- **Key:** `bd50097b-082d-4d9d-88aa-b0e47a1bb9cc`
- **Plan:** Lifetime Free (100 requests/day)
- **Env var:** `CRICAPI_KEY`
- **Endpoints:**
  - `GET /v1/currentMatches` → Live and upcoming matches
  - `GET /v1/cricScore` → Live ball-by-ball scores
  - `GET /v1/match_info?id=X` → Completed match result

### 2. OpenWeatherMap — Weather Forecast
- **URL:** https://openweathermap.org
- **Key:** `306c55b191ebc3b03e8ab0c952818365`
- **Plan:** Free (1,000 calls/day)
- **Env var:** `OPENWEATHER_KEY`
- **Used for:** Temperature, wind, humidity, rain for upcoming matches

### 3. Open-Meteo — Historical Weather
- **URL:** https://open-meteo.com
- **Key:** **None required — completely free**
- **Used for:** Historical weather for all 22,228 past matches

### 4. Open-Elevation — Venue Altitude
- **URL:** https://open-elevation.com
- **Key:** **None required — completely free**
- **Used for:** Altitude of each cricket ground

### 5. Cricsheet — Historical Match Data
- **URL:** https://cricsheet.org
- **Key:** **None required — completely free**
- **Size:** ~300MB, 22,228 matches in JSON format

### 6. Swiss Ephemeris — Astronomy
- **URL:** https://www.astro.com/swisseph
- **Key:** **None — LGPL Python library (pyswisseph)**
- **Used for:** Moon phase, Nakshatra, planet positions at match time

### 7. Supabase — Cloud Database
- **URL:** https://supabase.com
- **Key:** Provided by user (Supabase MCP keys)
- **Plan:** Free (500MB database)
- **Env var:** `SUPABASE_DB_URL`

### 8. Cloudflare — Public HTTPS Access
- **URL:** https://cloudflare.com
- **Key:** None for Quick Tunnel / Account for Named Tunnel
- **Cost:** Free forever

---

## Database Tables

| Table | Purpose | Location |
|---|---|---|
| `events` | Every cricket match | Local + Supabase |
| `cricket_match_metadata` | Match type, teams, toss | Local + Supabase |
| `teams` | Team names & IDs | Local + Supabase |
| `venues` | Ground names & locations | Local + Supabase |
| `innings` | Innings summary per match | Local + Supabase |
| `deliveries` | Raw ball-by-ball data | **Local ONLY** (1.3GB) |
| `features_statistics` | Computed cricket stats | Local + Supabase |
| `features_astronomy` | Computed astro features | Local + Supabase |
| `features_environment` | Computed weather features | Local + Supabase |
| `feature_registry` | Feature importance scores | Local + Supabase |
| `model_registry` | All trained models | Local + Supabase |
| `experiment_registry` | Training experiments | Local + Supabase |
| `prediction_store` | Every prediction ever made | Local + Supabase |
| `prediction_lineage` | Full audit trail per prediction | Local + Supabase |

---

## Key Files & Entry Points

| File | Purpose | Run Command |
|---|---|---|
| `etl_run.py` | Full ETL pipeline | `python etl_run.py --all` |
| `api.py` | FastAPI prediction server | `uvicorn api:app --port 8000` |
| `dashboard/app.py` | 12-page Streamlit UI | `streamlit run dashboard/app.py` |
| `scheduler.py` | Automated data + retrain | `python scheduler.py` |
| `migrate_to_supabase.py` | Push data to cloud DB | `python migrate_to_supabase.py` |
| `test_connectors.py` | Verify all API connections | `python test_connectors.py` |

---

## ETL Commands

```bash
python etl_run.py --download   # Download 22,228 Cricsheet JSON files
python etl_run.py --import     # Parse + insert into database
python etl_run.py --features   # Generate features for all matches
python etl_run.py --all        # Full pipeline (all 3 steps)
python etl_run.py --status     # Show database row counts
```

---

## Deployment Stack

```
Windows PC / VPS
│
├── Python 3.12 (no Docker needed)
├── Streamlit Dashboard (localhost:8501)
├── FastAPI API (localhost:8000)
├── APScheduler (background, automatic)
│
├── Local SQLite
│   └── Raw deliveries only (1.3GB, not in cloud)
│
└── Cloudflare Tunnel (free HTTPS)
        ↓
   Public Internet

Cloud:
├── Supabase (PostgreSQL, free 500MB)
│   └── All tables except raw deliveries
└── Cloudflare Tunnel (free)
```

---

## Quick Start

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Set up environment
copy .env.example .env
# Edit .env with your keys

# 3. Import all data (one-time, ~30 minutes)
python etl_run.py --all

# 4. Start the app (two terminals)
uvicorn api:app --host 0.0.0.0 --port 8000        # Terminal 1
streamlit run dashboard/app.py --server.port 8501  # Terminal 2

# 5. Expose publicly (Cloudflare Tunnel)
cloudflared tunnel --url http://localhost:8501      # Terminal 3
```

---

## Phase Completion Tracker

| Phase | Description | Status |
|---|---|---|
| 1 | Domain-agnostic schema + base ML engine | ✅ Complete |
| 2 | Walk-Forward Validation | ✅ Complete |
| 3 | Feature families (stats, astro, environment) | ✅ Complete |
| 4 | Scientific benchmarking + ablation | ✅ Complete |
| 5 | Research dashboards (SHAP, patterns, evolution) | ✅ Complete |
| 6 | Autonomous MLOps (Optuna, Champion/Challenger, Drift) | ✅ Complete |
| 7 | Live data connectors (CricAPI, OWM, Open-Meteo) | ✅ Complete |
| 8 | Production UI — 12-page Streamlit dashboard | ✅ Complete |
| 9 | Deployment (Cloudflare Tunnel, Nginx config) | ✅ Complete |
| 10 | Data lineage + prediction audit trail | ✅ Complete |
| 11 | Universal plugin framework | ✅ Complete |
| 12 | Supabase migration + cloud database | ⏳ In Progress |
