import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from sqlalchemy import create_engine

db_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
engine = create_engine(db_url)

st.set_page_config(page_title="Pattern Discovery", layout="wide")
st.title("🧩 Pattern Discovery Dashboard")
st.markdown("Automatically discover hidden correlations, new feature combinations, and unknown clusters.")

@st.cache_data(ttl=60)
def get_vector_embeddings():
    try:
        # Load sample vectors for clustering visualization
        query = "SELECT event_id, embedding FROM vectors LIMIT 1000"
        df = pd.read_sql(query, engine)
        
        # pgvector stores embeddings as strings '[0.1, 0.2, ...]' in some DBs, or arrays.
        # Parse them for UMAP/PCA
        def parse_emb(val):
            import ast
            if isinstance(val, str):
                return ast.literal_eval(val)
            return val
            
        df['embedding'] = df['embedding'].apply(parse_emb)
        return df
    except Exception as e:
        return pd.DataFrame()

df_vectors = get_vector_embeddings()

if df_vectors.empty:
    st.info("Loading simulated high-dimensional vectors for Pattern Discovery Engine...")
    np.random.seed(42)
    df_vectors = pd.DataFrame({
        'event_id': [f"match_{i}" for i in range(500)],
        'embedding': [np.random.rand(10).tolist() for _ in range(500)]
    })

st.subheader("High-Dimensional Cluster Discovery")
st.markdown("Projecting high-dimensional historical match features into 2D/3D space to reveal unmapped clusters.")

try:
    from sklearn.decomposition import PCA
    
    # Stack embeddings into matrix
    X = np.stack(df_vectors['embedding'].values)
    
    # PCA projection
    pca = PCA(n_components=3)
    components = pca.fit_transform(X)
    
    df_vectors['PCA1'] = components[:, 0]
    df_vectors['PCA2'] = components[:, 1]
    df_vectors['PCA3'] = components[:, 2]
    
    fig = px.scatter_3d(
        df_vectors, x='PCA1', y='PCA2', z='PCA3',
        hover_name='event_id',
        title="3D Match Cluster Projection",
        color_discrete_sequence=['#00e5ff']
    )
    fig.update_layout(scene=dict(bgcolor='#121212'), paper_bgcolor='#121212', font_color='white')
    st.plotly_chart(fig, use_container_width=True)
    
except ImportError:
    st.warning("scikit-learn is required for PCA cluster discovery.")

    st.subheader("Hidden Feature Correlations")
    st.markdown("*(Simulated)* The engine has detected a strong predictive non-linear correlation between **Venue Altitude** and **Toss Win** when **Moon Phase** is waning.")
    
    # Mocking a correlation heatmap
    np.random.seed(42)
    features = ['Altitude', 'TossWin', 'MoonPhase', 'Humidity', 'Temperature']
    corr_matrix = np.random.rand(5, 5)
    corr_matrix = (corr_matrix + corr_matrix.T) / 2
    np.fill_diagonal(corr_matrix, 1.0)
    
    fig_corr = px.imshow(
        corr_matrix, 
        x=features, 
        y=features,
        color_continuous_scale='Viridis',
        title="Discovered Feature Cross-Correlations"
    )
    st.plotly_chart(fig_corr, use_container_width=True)
