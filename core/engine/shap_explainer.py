import logging
from typing import Dict, Any, List
try:
    import shap
    import numpy as np
except ImportError:
    logging.warning("shap or numpy not installed. SHAP Explainer will be unavailable.")

from sqlalchemy.orm import Session
from sqlalchemy import text

class SHAPExplainer:
    """
    Integrates SHAP to demystify tree-based predictions and update the Feature Registry.
    """
    
    def __init__(self, engine):
        self.engine = engine

    def explain_and_update(self, model: Any, X_test: np.ndarray, feature_names: List[str]):
        """
        Calculates absolute mean SHAP values for global feature importance.
        Updates the DBFeatureRegistry table.
        """
        if 'shap' not in globals():
            return
            
        try:
            # TreeExplainer is best for XGBoost, Random Forest, LightGBM
            # Note: We must pass the raw estimator, not the CalibratedClassifierCV wrapper.
            # If model is CalibratedClassifierCV, we extract the base estimator
            base_model = model
            if hasattr(model, 'calibrated_classifiers_'):
                base_model = model.calibrated_classifiers_[0].estimator
                
            explainer = shap.TreeExplainer(base_model)
            shap_values = explainer.shap_values(X_test)
            
            # For binary classification, shap_values might be a list of 2 arrays, or 1 array.
            if isinstance(shap_values, list):
                shap_values = shap_values[1] # positive class
                
            # Calculate mean absolute SHAP value per feature
            mean_abs_shap = np.abs(shap_values).mean(axis=0)
            
            # Update database Feature Registry
            with Session(self.engine) as session:
                for feature_name, importance in zip(feature_names, mean_abs_shap):
                    # We use raw SQL for quick upsert
                    # In a robust system, we would query and update via ORM
                    # Here we exponentially decay the importance over walk-forward iterations
                    session.execute(text("""
                        UPDATE feature_registry 
                        SET baseline_importance = :imp,
                            usefulness_flag = CASE WHEN :imp > 0.001 THEN 1 ELSE 0 END
                        WHERE feature_name = :name
                    """), {"imp": float(importance), "name": feature_name})
                session.commit()
                
            logging.info(f"SHAP Explainer updated {len(feature_names)} features in the Registry.")
            
        except Exception as e:
            logging.error(f"SHAP explanation failed: {e}")
