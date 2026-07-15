import abc
from typing import List, Dict, Any, Type
import pandas as pd
import numpy as np
import sqlite3
import os
from sklearn.metrics import (
    log_loss, brier_score_loss, roc_auc_score, accuracy_score, 
    precision_score, recall_score, f1_score, matthews_corrcoef
)
from core.agents.super_agent import SuperAgentInterface
from core.scientific_audit.shap_analyzer import SHAPAnalyzer
from core.agents.signal_agents.planetary_agent import PlanetaryAgent

class WalkForwardTrainer:
    """
    Chronological training loop for the Meta-Learner (Super Agent).
    Evaluates models using a comprehensive scientific metric suite.
    """
    def __init__(self, db_path: str, model_class: Type[SuperAgentInterface]):
        self.db_path = db_path
        self.model_class = model_class
        self.conn = sqlite3.connect(db_path)
        
    def extract_dataset(self) -> pd.DataFrame:
        """
        In a full implementation, this extracts match history + all agent features.
        For Phase 2 validation, we'll extract base match stats + join with Kp index.
        """
        query = '''
            SELECT m.match_id, m.match_date, m.team1, m.team2, m.venue, m.toss_winner, m.winner,
                   k.kp_index as kp_exact_day -- Warning: this is just for structural testing, real features use Agent
            FROM matches m
            LEFT JOIN geomagnetic_kp k ON substr(m.match_date, 1, 10) = substr(k.timestamp, 1, 10)
            WHERE m.winner IS NOT NULL AND m.match_date IS NOT NULL
            ORDER BY m.match_date ASC
        '''
        df = pd.read_sql_query(query, self.conn)
        
        # Keep only matches where one of the two teams won (ignore ties/no result for binary classification)
        df = df[df['winner'].isin(df['team1']) | df['winner'].isin(df['team2'])].copy()
        
        # Create binary target: 1 if team1 wins, 0 if team2 wins
        df['target'] = (df['winner'] == df['team1']).astype(int)
        
        # Drop raw winner to prevent leakage
        df = df.drop(columns=['winner'])
        return df

    def run_validation(self, train_window_years=3, test_window_years=1):
        """
        Run a walk-forward validation.
        (e.g., train on 2004-2007, test on 2008. Then train 2005-2008, test 2009).
        """
        print("Generating Planetary Ephemeris features (this may take a moment)...")
        raw_df = self.extract_dataset()
        
        planetary_agent = PlanetaryAgent()
        
        feature_list = []
        for idx, row in raw_df.iterrows():
            date_str = str(row['match_date'])
            feats = planetary_agent.compute_features(row.to_dict(), date_str)
            feature_list.append(feats)
            
        planetary_df = pd.DataFrame(feature_list)
        df = pd.concat([raw_df.reset_index(drop=True), planetary_df.reset_index(drop=True)], axis=1)
        
        df['match_date'] = pd.to_datetime(df['match_date'], format='ISO8601', errors='coerce').dt.tz_localize(None)
        df = df.dropna(subset=['match_date'])
        
        start_year = df['match_date'].dt.year.min()
        max_year = df['match_date'].dt.year.max()
        
        print(f"Dataset spans {start_year} to {max_year}. {len(df)} matches.")
        
        all_y_true = []
        all_y_pred_proba = []
        all_y_pred_class = []
        
        # Walk forward loop
        current_year = start_year
        while current_year + train_window_years <= max_year:
            train_start = pd.Timestamp(year=current_year, month=1, day=1)
            train_end = pd.Timestamp(year=current_year + train_window_years, month=1, day=1)
            test_end = pd.Timestamp(year=current_year + train_window_years + test_window_years, month=1, day=1)
            
            train_df = df[(df['match_date'] >= train_start) & (df['match_date'] < train_end)].copy()
            test_df = df[(df['match_date'] >= train_end) & (df['match_date'] < test_end)].copy()
            
            if len(train_df) < 50 or len(test_df) == 0:
                current_year += test_window_years
                continue
                
            print(f"Training on {current_year}-{current_year+train_window_years-1} ({len(train_df)} matches). Testing on {current_year+train_window_years} ({len(test_df)} matches).")
            
            features = [
                'team1', 'team2', 'venue', 'toss_winner', 'kp_exact_day',
                'jupiter_sign', 'saturn_sign', 'mars_sign', 'sun_sign', 'moon_sign',
                'jupiter_retrograde', 'saturn_retrograde', 'mars_retrograde'
            ]
            
            X_train, y_train = train_df[features], train_df['target']
            X_test, y_test = test_df[features], test_df['target']
            
            agent = self.model_class()
            agent.train(X_train, y_train)
            
            # Predict
            probas = agent.predict_proba(X_test)[:, 1] # Probability of class 1
            preds = (probas > 0.5).astype(int)
            
            all_y_true.extend(y_test.values)
            all_y_pred_proba.extend(probas)
            all_y_pred_class.extend(preds)
            
            current_year += test_window_years

        self._compute_scientific_metrics(np.array(all_y_true), np.array(all_y_pred_proba), np.array(all_y_pred_class))
        
        # Run SHAP on the final model and test set
        if 'agent' in locals():
            shap_analyzer = SHAPAnalyzer(agent, X_test)
            shap_analyzer.generate_summary()

    def _compute_scientific_metrics(self, y_true: np.ndarray, y_proba: np.ndarray, y_pred: np.ndarray):
        print("\n" + "="*50)
        print("SCIENTIFIC EVALUATION METRICS (Leaderboard Suite)")
        print("="*50)
        
        if len(y_true) == 0:
            print("No predictions to evaluate.")
            return

        # Primary
        ll = log_loss(y_true, y_proba)
        print(f"Primary Metric (Log-Loss): {ll:.4f}")
        
        # Secondary
        print("-" * 50)
        print("Secondary Metrics:")
        print(f"Brier Score: {brier_score_loss(y_true, y_proba):.4f}")
        print(f"ROC-AUC:     {roc_auc_score(y_true, y_proba):.4f}")
        print(f"Accuracy:    {accuracy_score(y_true, y_pred):.4f}")
        print(f"Precision:   {precision_score(y_true, y_pred, zero_division=0):.4f}")
        print(f"Recall:      {recall_score(y_true, y_pred, zero_division=0):.4f}")
        print(f"F1 Score:    {f1_score(y_true, y_pred, zero_division=0):.4f}")
        print(f"MCC:         {matthews_corrcoef(y_true, y_pred):.4f}")
        
        # Calibration Error (Expected Calibration Error - ECE)
        # Simple implementation using 10 bins
        bins = np.linspace(0, 1, 11)
        binids = np.digitize(y_proba, bins) - 1
        bin_sums = np.bincount(binids, weights=y_proba, minlength=len(bins))
        bin_true = np.bincount(binids, weights=y_true, minlength=len(bins))
        bin_total = np.bincount(binids, minlength=len(bins))
        
        nonzero = bin_total != 0
        prob_pred = bin_sums[nonzero] / bin_total[nonzero]
        prob_true = bin_true[nonzero] / bin_total[nonzero]
        ece = np.sum(np.abs(prob_true - prob_pred) * (bin_total[nonzero] / len(y_true)))
        print(f"ECE:         {ece:.4f}")
        print("="*50)
