import logging
import pandas as pd
from typing import List, Dict

class DataQualityGateway:
    """
    Validates data quality before allowing it to enter the ML pipeline.
    Stops training/ingestion if data quality is compromised.
    """
    
    @staticmethod
    def validate_dataset(df: pd.DataFrame, expected_columns: List[str]) -> bool:
        """
        Runs rigorous checks:
        1. Missing critical columns
        2. Missing values in critical columns
        3. Duplicates
        4. Invalid dates
        """
        logging.info(f"Validating dataset of shape {df.shape}")
        
        # 1. Missing columns
        missing_cols = [c for c in expected_columns if c not in df.columns]
        if missing_cols:
            logging.error(f"DataQualityError: Missing columns {missing_cols}")
            return False
            
        # 2. Missing values
        if df[expected_columns].isnull().any().any():
            logging.error("DataQualityError: Found missing values in critical columns.")
            return False
            
        # 3. Duplicates
        if df.duplicated(subset=['match_id']).any():
            logging.error("DataQualityError: Duplicate match_ids found.")
            return False
            
        # 4. Invalid dates (Future dates not allowed in historical training data)
        if 'date' in df.columns:
            if pd.to_datetime(df['date']).max() > pd.Timestamp.utcnow():
                logging.error("DataQualityError: Training data contains future dates.")
                return False
                
        logging.info("Dataset passed quality validation.")
        return True

class MultiSourceVerifier:
    """
    Cross-checks data from multiple API providers.
    If Cricsheet says Team A won, but SportMonks says Team B won, it flags an anomaly.
    """
    
    @staticmethod
    def verify_match_outcome(primary_source: Dict, secondary_source: Dict) -> bool:
        """
        Returns True if sources agree, False if there is a conflict.
        """
        p_winner = primary_source.get("winner")
        s_winner = secondary_source.get("winner")
        
        if p_winner != s_winner:
            logging.error(f"MultiSourceConflict: Primary says {p_winner}, Secondary says {s_winner}.")
            return False
            
        return True
