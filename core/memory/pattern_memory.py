import logging
from typing import List, Dict, Any, Tuple
try:
    import numpy as np
    from sklearn.preprocessing import StandardScaler
except ImportError:
    logging.warning("scikit-learn or numpy not installed. Pattern Memory will be unavailable.")

from sqlalchemy.orm import Session
from sqlalchemy import text
from core.memory.schema import DBVector, DBEvent

class PatternMemoryEngine:
    """
    Manages the encoding, storage, and retrieval of match feature vectors
    using pgvector for similarity searches.
    """
    
    def __init__(self, engine):
        self.engine = engine
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def fit_scaler(self, X_historical: np.ndarray):
        """Fits the StandardScaler on the historical dataset to normalize vectors."""
        self.scaler.fit(X_historical)
        self.is_fitted = True
        
    def encode(self, X: np.ndarray) -> np.ndarray:
        """Standardizes the raw feature vectors."""
        if not self.is_fitted:
            logging.warning("StandardScaler not fitted. Encoding without normalization.")
            return X
        return self.scaler.transform(X)
        
    def store_vectors(self, match_ids: List[str], X_encoded: np.ndarray):
        """Stores the encoded vectors in the DBVector table."""
        with Session(self.engine) as session:
            for match_id, vector in zip(match_ids, X_encoded):
                # Using SQLAlchemy ORM for pgvector
                # We assume DBVector.embedding is a pgvector Vector column
                vec_record = session.query(DBVector).filter_by(event_id=match_id).first()
                if not vec_record:
                    vec_record = DBVector(event_id=match_id)
                    session.add(vec_record)
                vec_record.embedding = vector.tolist()
            session.commit()
            
    def search_similar(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves the top K most similar historical matches using L2 distance (<->).
        Returns the match details and explainability metrics.
        """
        # Ensure it's a 1D list
        vec_list = query_vector.flatten().tolist()
        
        # pgvector syntax: embedding <-> '[...]' (L2 distance)
        # We join with Events to get the historical winner
        sql = text("""
            SELECT v.event_id, e.date, e.venue_id, e.outcome, (v.embedding <-> :vec) as distance
            FROM vectors v
            JOIN events e ON v.event_id = e.id
            ORDER BY v.embedding <-> :vec
            LIMIT :k
        """)
        
        results = []
        with Session(self.engine) as session:
            rows = session.execute(sql, {"vec": str(vec_list), "k": top_k}).all()
            
            for row in rows:
                results.append({
                    "match_id": row.event_id,
                    "date": str(row.date),
                    "venue": row.venue_id,
                    "historical_winner": row.outcome,
                    "distance_score": float(row.distance)
                })
                
        return results
