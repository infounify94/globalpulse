import logging
from typing import Dict, Any, List
try:
    import numpy as np
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, log_loss, brier_score_loss, confusion_matrix
    )
except ImportError:
    logging.warning("scikit-learn is not installed. Metrics will be unavailable.")

class ModelMetrics:
    """
    Computes a comprehensive suite of evaluation metrics for classification models.
    """
    
    @staticmethod
    def evaluate(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray = None) -> Dict[str, Any]:
        """
        Evaluates predictions against true labels.
        y_true: array of actual outcomes (0 or 1)
        y_pred: array of predicted outcomes (0 or 1)
        y_prob: array of predicted probabilities for the positive class (optional, but required for log loss, ROC, Brier)
        """
        metrics = {}
        
        try:
            metrics["accuracy"] = float(accuracy_score(y_true, y_pred))
            metrics["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
            metrics["recall"] = float(recall_score(y_true, y_pred, zero_division=0))
            metrics["f1_score"] = float(f1_score(y_true, y_pred, zero_division=0))
            
            # Confusion matrix
            cm = confusion_matrix(y_true, y_pred)
            metrics["confusion_matrix"] = cm.tolist()
            
            if y_prob is not None:
                metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
                metrics["log_loss"] = float(log_loss(y_true, y_prob))
                metrics["brier_score"] = float(brier_score_loss(y_true, y_prob))
                
                # Calibration Error (Expected Calibration Error - ECE)
                # Simplified 10-bin ECE calculation
                bins = np.linspace(0., 1., 11)
                binids = np.digitize(y_prob, bins) - 1
                
                bin_sums = np.bincount(binids, weights=y_prob, minlength=len(bins))
                bin_true = np.bincount(binids, weights=y_true, minlength=len(bins))
                bin_total = np.bincount(binids, minlength=len(bins))
                
                nonzero = bin_total != 0
                prob_pred = bin_sums[nonzero] / bin_total[nonzero]
                prob_true = bin_true[nonzero] / bin_total[nonzero]
                
                ece = np.sum(np.abs(prob_pred - prob_true) * (bin_total[nonzero] / len(y_true)))
                metrics["calibration_error_ece"] = float(ece)
                
        except Exception as e:
            logging.error(f"Error calculating metrics: {e}")
            
        return metrics
