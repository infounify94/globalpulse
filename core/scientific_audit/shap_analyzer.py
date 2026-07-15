import abc
import pandas as pd
import numpy as np

class SHAPAnalyzer:
    """
    Computes SHAP (SHapley Additive exPlanations) values to mathematically prove 
    exactly how much signal an agent contributes compared to baseline statistics.
    """
    def __init__(self, model_interface, X_test: pd.DataFrame):
        self.model = model_interface.model
        self.X_test = X_test
        self._is_available = True
        try:
            import shap
            self.shap = shap
        except ImportError:
            print("Warning: shap is not installed. Run 'pip install shap'.")
            self._is_available = False

    def generate_summary(self):
        if not self._is_available or self.model is None:
            print("SHAP analysis unavailable.")
            return
            
        print("\n" + "="*50)
        print("SHAP FEATURE IMPORTANCE ANALYSIS")
        print("="*50)
        
        try:
            # TreeExplainer is fast for CatBoost/XGBoost
            explainer = self.shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(self.X_test)
            
            # For CatBoost classifier, shap_values might be a list (one for each class)
            if isinstance(shap_values, list):
                shap_values = shap_values[1] # Take positive class
                
            # Calculate mean absolute SHAP value for each feature
            mean_abs_shap = np.abs(shap_values).mean(axis=0)
            
            importance_df = pd.DataFrame({
                'Feature': self.X_test.columns,
                'Mean |SHAP|': mean_abs_shap
            }).sort_values('Mean |SHAP|', ascending=False)
            
            print(importance_df.to_string(index=False))
            print("="*50)
        except Exception as e:
            print(f"Error calculating SHAP values: {e}")
