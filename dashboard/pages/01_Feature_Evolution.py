import streamlit as st
import pandas as pd
import os
import plotly.express as px
from sqlalchemy import create_engine

# Setup DB connection
db_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
engine = create_engine(db_url)

st.set_page_config(page_title="Feature Evolution", layout="wide")
st.title("🧬 Feature Evolution Dashboard")
st.markdown("Track the Top 100 important features, features losing importance, and newly discovered useful features.")

@st.cache_data(ttl=60)
def get_features():
    try:
        # Load features from Feature Registry
        query = """
        SELECT feature_name, family, baseline_importance, usefulness_flag
        FROM feature_registry
        ORDER BY baseline_importance DESC
        """
        return pd.read_sql(query, engine)
    except Exception as e:
        return pd.DataFrame()

df_features = get_features()

if df_features.empty:
    st.info("Feature Registry is empty. Run Phase 4 Ablation and SHAP testing.")
else:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Top Important Features")
        top_10 = df_features[df_features['usefulness_flag'] == True].head(10)
        st.dataframe(top_10[['feature_name', 'family', 'baseline_importance']])
        
    with col2:
        st.subheader("Features Losing Importance / Removed")
        removed = df_features[df_features['usefulness_flag'] == False]
        st.dataframe(removed[['feature_name', 'family']])
        
    with col3:
        st.subheader("Newly Discovered (Mocked)")
        st.info("New combinations discovered via ablation tests.")
        st.markdown("- Venue Altitude x Toss Win")
        st.markdown("- Recent 5 Wins x Moon Phase")
        
    st.subheader("Global Importance Distribution")
    fig = px.bar(
        df_features.head(25), 
        x='baseline_importance', 
        y='feature_name', 
        color='family', 
        orientation='h',
        title="Top 25 Features by Baseline Importance"
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
