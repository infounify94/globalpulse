import streamlit as st
import pandas as pd
import os
import plotly.express as px
from sqlalchemy import create_engine

db_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
engine = create_engine(db_url)

st.set_page_config(page_title="Model Evolution", layout="wide")
st.title("📈 Model Evolution Dashboard")
st.markdown("Track prediction engine improvements across all walk-forward training cycles.")

@st.cache_data(ttl=60)
def get_model_history():
    query = """
    SELECT m.id, m.algorithm, m.test_end_year, m.performance_metrics, e.start_time
    FROM model_registry m
    JOIN experiment_registry e ON m.experiment_id = e.id
    ORDER BY e.start_time ASC
    """
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        return pd.DataFrame()

df_models = get_model_history()

if df_models.empty:
    st.info("No models trained yet.")
else:
    # Parse metrics
    df_models['Accuracy'] = df_models['performance_metrics'].apply(lambda x: float(eval(x).get('accuracy', 0)) if isinstance(x, str) else x.get('accuracy', 0))
    df_models['BrierScore'] = df_models['performance_metrics'].apply(lambda x: float(eval(x).get('brier_score', 0)) if isinstance(x, str) else x.get('brier_score', 0))
    df_models['Iteration'] = range(1, len(df_models) + 1)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Accuracy Improvement (V1 to VN)")
        fig_acc = px.line(df_models, x='Iteration', y='Accuracy', color='algorithm', markers=True, title="Accuracy over Training Cycles")
        st.plotly_chart(fig_acc, use_container_width=True)
        
    with col2:
        st.subheader("Brier Score Evolution (Lower is better)")
        fig_brier = px.line(df_models, x='Iteration', y='BrierScore', color='algorithm', markers=True, title="Brier Score over Training Cycles")
        fig_brier.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_brier, use_container_width=True)
        
    st.subheader("Detailed Model Log")
    st.dataframe(df_models[['Iteration', 'id', 'algorithm', 'test_end_year', 'Accuracy', 'BrierScore']])
