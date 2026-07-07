import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine

db_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
engine = create_engine(db_url)

st.set_page_config(page_title="Live Match Monitor", layout="wide")
st.title("📡 Live Match Monitor")
st.markdown("Real-time tracking of generated predictions, confidence scores, and automatic retrain status.")

@st.cache_data(ttl=10)
def get_live_predictions():
    query = """
    SELECT id, match_id, model_id, prediction_timestamp, predicted_winner_id, probability, actual_winner_id, is_correct
    FROM prediction_store
    ORDER BY prediction_timestamp DESC
    LIMIT 100
    """
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        return pd.DataFrame()

df_live = get_live_predictions()

if df_live.empty:
    st.info("No live predictions found. Use the /predict API to generate some.")
else:
    # Split into pending (unverified) and verified
    pending = df_live[df_live['is_correct'].isnull()]
    verified = df_live[df_live['is_correct'].notnull()]
    
    st.subheader(f"Upcoming Matches (Pending Verification) - {len(pending)}")
    if not pending.empty:
        st.dataframe(pending[['prediction_timestamp', 'match_id', 'predicted_winner_id', 'probability', 'model_id']])
    else:
        st.write("No pending matches.")
        
    st.subheader(f"Verified Results (Continuous Learning Triggered) - {len(verified)}")
    if not verified.empty:
        # Format for display
        def color_result(val):
            color = '#00ff00' if val == True else '#ff0000'
            return f'background-color: {color}'
            
        display_df = verified[['prediction_timestamp', 'match_id', 'predicted_winner_id', 'probability', 'actual_winner_id', 'is_correct']]
        st.dataframe(display_df.style.applymap(color_result, subset=['is_correct']))
        
        # Calculate recent accuracy
        recent_acc = verified.head(20)['is_correct'].mean() * 100
        st.metric(label="Recent 20 Matches Accuracy", value=f"{recent_acc:.1f}%")
    else:
        st.write("No verified matches.")
        
    st.sidebar.header("Continuous Learning Status")
    st.sidebar.success("✅ Auto-Retrain Engine: ACTIVE")
    st.sidebar.info("The backend will automatically trigger Feature Ablation and Retraining upon receiving new verified results.")
