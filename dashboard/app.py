"""
GlobalPulse Production Dashboard — Main Application
12-page professional research & operations platform.
Dark theme, Plotly charts, search, filters, CSV export.
"""
import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

# ── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GlobalPulse",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Global Dark Theme CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0d1117;
        color: #e6edf3;
    }
    .stApp { background-color: #0d1117; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-right: 1px solid #30363d;
    }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: border-color 0.2s;
    }
    .metric-card:hover { border-color: #58a6ff; }
    .metric-value { font-size: 2.2rem; font-weight: 700; color: #58a6ff; }
    .metric-label { font-size: 0.85rem; color: #8b949e; margin-top: 4px; }
    .status-ok { color: #3fb950; font-weight: 600; }
    .status-warn { color: #d29922; font-weight: 600; }
    .status-err { color: #f85149; font-weight: 600; }
    .section-header {
        font-size: 1.4rem; font-weight: 600; color: #e6edf3;
        border-bottom: 2px solid #21262d; padding-bottom: 8px; margin: 24px 0 16px;
    }
    div[data-testid="stDataFrame"] { border-radius: 8px; }
    .stButton button {
        background: #238636; color: white; border: none;
        border-radius: 6px; font-weight: 500;
    }
    .stButton button:hover { background: #2ea043; }
</style>
""", unsafe_allow_html=True)

# ── DB Connection ────────────────────────────────────────────────────────────
if "GLOBALPULSE_DB_URL" in st.secrets:
    DB_URL = st.secrets["GLOBALPULSE_DB_URL"]
else:
    DB_URL = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")

@st.cache_resource
def get_engine():
    return create_engine(DB_URL, pool_pre_ping=True)

engine = get_engine()

def safe_query(sql: str, params=None) -> pd.DataFrame:
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    except Exception as e:
        import streamlit as st
        st.error(f"Database Error: {e}")
        return pd.DataFrame()

# ── Sidebar Navigation ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔮 GlobalPulse")
    st.markdown("<hr style='border-color:#30363d'>", unsafe_allow_html=True)
    st.markdown("**Navigation**")

    pages = {
        "📊 Dashboard":            "dashboard",
        "🏏 Upcoming Matches":     "upcoming",
        "🎯 Prediction Details":   "predictions",
        "📜 Historical Predictions":"history",
        "📈 Model Performance":    "model_perf",
        "🧩 Pattern Explorer":     "patterns",
        "🧬 Feature Importance":   "features",
        "🏥 Data Health":          "data_health",
        "🧪 Experiment History":   "experiments",
        "🔄 Retraining Status":    "retrain",
        "⚙️ Settings":             "settings",
        "📋 Logs":                 "logs",
    }
    selected = st.radio("Navigation", list(pages.keys()), label_visibility="collapsed")
    page = pages[selected]

    st.markdown("<hr style='border-color:#30363d'>", unsafe_allow_html=True)
    st.caption(f"DB: `{DB_URL.split('/')[-1]}`")
    st.caption(f"Mode: `{os.environ.get('GLOBALPULSE_MODE','production')}`")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Dashboard
# ═══════════════════════════════════════════════════════════════════════════
if page == "dashboard":
    st.markdown("# 📊 GlobalPulse Dashboard")
    st.caption("Operational overview of the prediction engine")

    df_preds = safe_query(
        "SELECT is_correct, probability, prediction_timestamp FROM prediction_store "
        "WHERE is_correct IS NOT NULL ORDER BY prediction_timestamp DESC LIMIT 200"
    )
    df_models = safe_query("SELECT * FROM model_registry ORDER BY rowid DESC LIMIT 1")
    df_events = safe_query("SELECT COUNT(*) as cnt FROM events")

    total_matches = df_events['cnt'].iloc[0] if not df_events.empty else 0
    total_preds   = len(df_preds)
    accuracy      = df_preds['is_correct'].mean() * 100 if not df_preds.empty else 0
    champ_algo    = df_models['algorithm'].iloc[0] if not df_models.empty else "None"

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label in [
        (c1, f"{total_matches:,}", "Total Matches"),
        (c2, f"{total_preds:,}", "Predictions Made"),
        (c3, f"{accuracy:.1f}%", "Recent Accuracy"),
        (c4, champ_algo, "Champion Model"),
    ]:
        col.markdown(
            f'<div class="metric-card"><div class="metric-value">{val}</div>'
            f'<div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown('<p class="section-header">Accuracy Over Time</p>', unsafe_allow_html=True)
    if not df_preds.empty:
        df_preds['prediction_timestamp'] = pd.to_datetime(df_preds['prediction_timestamp'])
        df_preds['correct_int'] = df_preds['is_correct'].astype(int)
        df_time = df_preds.set_index('prediction_timestamp').resample('W')['correct_int'].mean().reset_index()
        fig = px.line(df_time, x='prediction_timestamp', y='correct_int',
                      labels={'correct_int': 'Accuracy', 'prediction_timestamp': 'Week'},
                      title="Weekly Prediction Accuracy",
                      template="plotly_dark", color_discrete_sequence=["#58a6ff"])
        fig.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117', yaxis_tickformat='.0%')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No verified predictions yet. Run the ETL pipeline and train a model first.")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Upcoming Matches
# ═══════════════════════════════════════════════════════════════════════════
elif page == "upcoming":
    st.markdown("# 🏏 Upcoming Matches")
    st.caption("Auto-generated predictions for all upcoming matches")

    df_upcoming = safe_query(
        "SELECT e.id, e.date, e.venue_id, m.team_a_id, m.team_b_id, m.match_type, "
        "p.probability, p.confidence, p.predicted_winner_id, p.model_id "
        "FROM events e "
        "JOIN cricket_match_metadata m ON e.id = m.event_id "
        "LEFT JOIN prediction_store p ON e.id = p.match_id "
        "WHERE e.outcome IS NULL ORDER BY e.date ASC LIMIT 50"
    )

    if df_upcoming.empty:
        st.info("No upcoming matches found. The scheduler will auto-populate this when live data is connected.")
        st.markdown("**Simulated Example:**")
        df_upcoming = pd.DataFrame([
            {"team_a_id": "india", "team_b_id": "australia", "date": "2026-07-10",
             "match_type": "ODI", "venue_id": "wankhede_stadium",
             "probability": 0.67, "confidence": 0.72, "predicted_winner_id": "india",
             "model_id": "champion_v3"}
        ])

    col_a, col_b = st.columns([3, 1])
    with col_b:
        if st.button("📥 Export CSV"):
            st.download_button("Download", df_upcoming.to_csv(index=False), "upcoming.csv")

    st.dataframe(
        df_upcoming.style.background_gradient(subset=['probability'] if 'probability' in df_upcoming.columns else [],
                                              cmap='RdYlGn'),
        use_container_width=True
    )

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Historical Predictions
# ═══════════════════════════════════════════════════════════════════════════
elif page == "history":
    st.markdown("# 📜 Historical Predictions")

    df = safe_query(
        "SELECT id, match_id, predicted_winner_id, probability, confidence, "
        "actual_winner_id, is_correct, prediction_timestamp, model_id "
        "FROM prediction_store ORDER BY prediction_timestamp DESC"
    )

    if df.empty:
        st.info("No predictions stored yet.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Predictions", len(df))
        col2.metric("Correct", int(df['is_correct'].sum()))
        col3.metric("Accuracy", f"{df['is_correct'].mean()*100:.1f}%" if df['is_correct'].notna().any() else "N/A")

        # Filters
        search = st.text_input("🔍 Search by Match ID or Team")
        if search:
            df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

        correct_filter = st.selectbox("Filter by Result", ["All", "Correct Only", "Incorrect Only"])
        if correct_filter == "Correct Only":
            df = df[df['is_correct'] == True]
        elif correct_filter == "Incorrect Only":
            df = df[df['is_correct'] == False]

        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Export CSV", df.to_csv(index=False), "predictions.csv")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Model Performance
# ═══════════════════════════════════════════════════════════════════════════
elif page == "model_perf":
    st.markdown("# 📈 Model Performance")

    df = safe_query(
        "SELECT m.id, m.algorithm, m.test_end_year, m.performance_metrics, "
        "m.calibration_metrics, m.execution_time_seconds, m.is_champion "
        "FROM model_registry m ORDER BY m.test_end_year, m.algorithm"
    )

    if df.empty:
        st.info("No models trained yet. Run the walk-forward pipeline.")
    else:
        def safe_metric(val, key):
            try:
                d = val if isinstance(val, dict) else __import__('json').loads(val)
                return float(d.get(key, 0))
            except Exception:
                return 0.0

        df['Accuracy']   = df['performance_metrics'].apply(lambda x: safe_metric(x, 'accuracy'))
        df['Brier']      = df['performance_metrics'].apply(lambda x: safe_metric(x, 'brier_score'))
        df['ROC_AUC']    = df['performance_metrics'].apply(lambda x: safe_metric(x, 'roc_auc'))
        df['Champion']   = df['is_champion'].apply(lambda x: "👑 Champion" if x else "")

        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(df, x='test_end_year', y='Accuracy', color='algorithm',
                          markers=True, title="Accuracy per Walk-Forward Year",
                          template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Plotly)
            fig.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.line(df, x='test_end_year', y='Brier', color='algorithm',
                          markers=True, title="Brier Score (lower = better)",
                          template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Plotly)
            fig.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117')
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<p class="section-header">Model Leaderboard</p>', unsafe_allow_html=True)
        display_df = df[['Champion', 'algorithm', 'test_end_year', 'Accuracy', 'Brier', 'ROC_AUC', 'execution_time_seconds']].copy()
        display_df.columns = ['', 'Algorithm', 'Test Year', 'Accuracy', 'Brier Score', 'ROC-AUC', 'Train Time (s)']
        st.dataframe(display_df.sort_values('Accuracy', ascending=False), use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Feature Importance
# ═══════════════════════════════════════════════════════════════════════════
elif page == "features":
    st.markdown("# 🧬 Feature Importance")
    df = safe_query(
        "SELECT feature_name, family, baseline_importance, usefulness_flag "
        "FROM feature_registry ORDER BY baseline_importance DESC"
    )

    if df.empty:
        st.info("Feature registry is empty. Run Phase 4 Walk-Forward + Ablation to populate it.")
    else:
        c1, c2 = st.columns(2)
        c1.metric("Total Features", len(df))
        c2.metric("Active Features", int(df['usefulness_flag'].sum()))

        top_n = st.slider("Show Top N features", 10, 100, 25)
        fig = px.bar(df.head(top_n), x='baseline_importance', y='feature_name',
                     color='family', orientation='h',
                     title=f"Top {top_n} Features by Importance",
                     template="plotly_dark")
        fig.update_layout(yaxis={'categoryorder': 'total ascending'},
                          paper_bgcolor='#161b22', plot_bgcolor='#0d1117', height=600)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Removed / Dead Features**")
        dead = df[df['usefulness_flag'] == False]
        if dead.empty:
            st.success("No dead features detected.")
        else:
            st.dataframe(dead[['feature_name', 'family', 'baseline_importance']], use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Data Health
# ═══════════════════════════════════════════════════════════════════════════
elif page == "data_health":
    st.markdown("# 🏥 Data Health Monitor")

    tables = [
        ("events", "📅 Events"),
        ("cricket_match_metadata", "🏏 Cricket Metadata"),
        ("innings", "🏃 Innings"),
        ("features_statistics", "📊 Statistical Features"),
        ("features_astronomy", "🔭 Astronomical Features"),
        ("features_environment", "🌦️ Environment Features"),
        ("model_registry", "🤖 Models"),
        ("prediction_store", "🎯 Predictions"),
    ]

    cols = st.columns(4)
    for i, (tbl, label) in enumerate(tables):
        df = safe_query(f"SELECT COUNT(*) as cnt FROM {tbl}")
        count = df['cnt'].iloc[0] if not df.empty else 0
        status = "🟢" if count > 0 else "⚪"
        cols[i % 4].metric(f"{status} {label}", f"{count:,}")

    st.markdown('<p class="section-header">ETL Log (last 50 lines)</p>', unsafe_allow_html=True)
    if os.path.exists("etl.log"):
        with open("etl.log", "r") as f:
            lines = f.readlines()[-50:]
        st.code("".join(lines), language="text")
    else:
        st.info("No ETL log found. Run `python etl_run.py --all` to populate data.")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Experiment History
# ═══════════════════════════════════════════════════════════════════════════
elif page == "experiments":
    st.markdown("# 🧪 Experiment History")
    df = safe_query(
        "SELECT id, start_time, end_time, dataset_version, feature_version, "
        "feature_families_tested, winning_model_id FROM experiment_registry ORDER BY start_time DESC"
    )
    if df.empty:
        st.info("No experiments run yet.")
    else:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Export CSV", df.to_csv(index=False), "experiments.csv")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Retraining Status
# ═══════════════════════════════════════════════════════════════════════════
elif page == "retrain":
    st.markdown("# 🔄 Retraining & Model Lifecycle")

    df = safe_query(
        "SELECT id, algorithm, test_end_year, is_champion, "
        "performance_metrics, model_artifact_path FROM model_registry ORDER BY rowid DESC LIMIT 20"
    )

    if df.empty:
        st.info("No models found. Run the training pipeline first.")
    else:
        champion_row = df[df['is_champion'] == True]
        if not champion_row.empty:
            row = champion_row.iloc[0]
            st.success(f"👑 **Current Champion**: `{row['id']}` — Algorithm: `{row['algorithm']}`")
            st.info(f"Artifact: `{row.get('model_artifact_path', 'N/A')}`")
        else:
            st.warning("⚠️ No Champion model promoted yet. Run walk-forward training to generate one.")

        st.markdown("**Drift Monitoring**")
        df_drift = safe_query(
            "SELECT is_correct FROM prediction_store "
            "WHERE is_correct IS NOT NULL ORDER BY prediction_timestamp DESC LIMIT 50"
        )
        if not df_drift.empty:
            recent_acc = df_drift['is_correct'].mean() * 100
            if recent_acc >= 60:
                st.markdown(f'<span class="status-ok">✅ No drift detected — Recent accuracy: {recent_acc:.1f}%</span>', unsafe_allow_html=True)
            elif recent_acc >= 50:
                st.markdown(f'<span class="status-warn">⚠️ Drift Warning — Accuracy: {recent_acc:.1f}%</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="status-err">🚨 Drift Alert — Accuracy: {recent_acc:.1f}% — Retraining recommended!</span>', unsafe_allow_html=True)
        else:
            st.info("Not enough verified predictions for drift analysis (need ≥ 50).")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Settings
# ═══════════════════════════════════════════════════════════════════════════
elif page == "settings":
    st.markdown("# ⚙️ Settings")

    st.markdown("**Execution Mode**")
    mode = st.selectbox("Mode", ["production", "research"],
                        index=0 if os.environ.get("GLOBALPULSE_MODE", "production") == "production" else 1)
    st.caption("Research: Enables Optuna and experimental features. Production: Champion model only.")

    st.markdown("**API Connectors**")
    cricapi_key = st.text_input("CricAPI Key", value=os.environ.get("CRICAPI_KEY", ""),
                                type="password", help="Get free key at cricapi.com")
    if cricapi_key:
        st.success("✅ CricAPI Key configured")
    else:
        st.warning("⚠️ No CricAPI Key — using mock data for live schedules")

    st.markdown("**Database**")
    st.code(DB_URL)

    st.markdown("**Data Quality Thresholds**")
    drift_threshold = st.slider("Drift Alert Threshold (accuracy %)", 40, 70, 55)
    st.caption(f"Alert will trigger if recent accuracy drops below {drift_threshold}%")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Logs
# ═══════════════════════════════════════════════════════════════════════════
elif page == "logs":
    st.markdown("# 📋 System Logs")

    log_files = {"ETL Log": "etl.log", "Scheduler Log": "scheduler.log"}
    selected_log = st.selectbox("Log File", list(log_files.keys()))
    log_path = log_files[selected_log]
    severity = st.multiselect("Filter Severity", ["INFO", "WARNING", "ERROR"], default=["WARNING", "ERROR"])
    lines_to_show = st.slider("Lines to show", 20, 500, 100)

    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            all_lines = f.readlines()

        filtered = [l for l in all_lines if any(s in l for s in severity)] if severity else all_lines
        filtered = filtered[-lines_to_show:]
        st.code("".join(filtered) if filtered else "No matching log entries.", language="text")
        st.download_button("📥 Download Full Log", "".join(all_lines), log_path)
    else:
        st.info(f"Log file `{log_path}` not found yet.")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Pattern Explorer (redirects to existing page)
# ═══════════════════════════════════════════════════════════════════════════
elif page == "patterns":
    st.markdown("# 🧩 Pattern Explorer")
    st.info("Loading Pattern Discovery Engine...")
    exec(open("dashboard/pages/03_Pattern_Discovery.py").read() if os.path.exists("dashboard/pages/03_Pattern_Discovery.py") else "st.error('Pattern Discovery page not found.')")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Prediction Details
# ═══════════════════════════════════════════════════════════════════════════
elif page == "predictions":
    st.markdown("# 🎯 Prediction Details & Lineage")

    pred_id = st.text_input("Enter Prediction ID (from Historical Predictions page)")
    if pred_id:
        df_pred = safe_query(
            "SELECT * FROM prediction_store WHERE id = :pid", params={"pid": pred_id}
        )
        df_lineage = safe_query(
            "SELECT * FROM prediction_lineage WHERE prediction_id = :pid", params={"pid": pred_id}
        )
        if not df_pred.empty:
            st.markdown("**Prediction Record**")
            st.json(df_pred.iloc[0].to_dict())
        if not df_lineage.empty:
            st.markdown("**Full Data Lineage Audit Trail**")
            st.json(df_lineage.iloc[0].to_dict())
        elif pred_id:
            st.warning("Lineage record not found for this prediction ID.")
