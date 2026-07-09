import os
import sqlite3
import pandas as pd
import numpy as np

def run_betting_audit():
    conn = sqlite3.connect('globalpulse_dev.db')
    
    # 1. Get Champion Model
    champion_df = pd.read_sql("SELECT * FROM model_registry WHERE id LIKE 'sci_audit%' ORDER BY CAST(json_extract(performance_metrics, '$.accuracy') AS REAL) DESC LIMIT 1", conn)
    if champion_df.empty:
        print("No champion found.")
        return
        
    champion_id = champion_df['id'].iloc[0]
    
    # 2. Get predictions
    preds = pd.read_sql(f"SELECT * FROM prediction_store WHERE model_id = '{champion_id}'", conn)
    
    # 3. Betting ROI Simulation (Flat stake = 100)
    stake = 100
    # True win pays approx 1.9 (assuming even bookie margin of 5%)
    odds = 1.9
    
    # Strategy: bet if confidence > 0.50
    preds['bet_won'] = preds['is_correct'] == 1
    
    total_bets = len(preds)
    total_staked = total_bets * stake
    total_return = preds['bet_won'].sum() * (stake * odds)
    
    profit = total_return - total_staked
    roi = (profit / total_staked) * 100 if total_staked > 0 else 0
    
    # Max Drawdown
    preds['pnl'] = np.where(preds['bet_won'], stake * (odds - 1), -stake)
    cumulative_pnl = preds['pnl'].cumsum()
    rolling_max = cumulative_pnl.cummax()
    drawdown = rolling_max - cumulative_pnl
    max_drawdown = drawdown.max()
    
    betting_report = pd.DataFrame({
        "Metric": ["Total Bets", "Total Staked", "Total Profit", "ROI", "Max Drawdown"],
        "Value": [total_bets, f"₹{total_staked}", f"₹{profit:.2f}", f"{roi:.2f}%", f"₹{max_drawdown:.2f}"]
    })
    betting_report.to_csv("scientific_audit/betting_roi.csv", index=False)
    
    # 4. Confidence Threshold Analysis
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
    thresh_data = []
    
    for t in thresholds:
        mask = preds['probability'] >= t
        if mask.sum() > 0:
            subset = preds[mask]
            acc = subset['is_correct'].mean()
            coverage = len(subset) / len(preds)
            t_profit = subset['pnl'].sum()
            t_roi = (t_profit / (len(subset) * stake)) * 100
            thresh_data.append({
                "Threshold": f"> {t*100:.0f}%",
                "Accuracy": f"{acc*100:.2f}%",
                "Coverage": f"{coverage*100:.2f}%",
                "ROI": f"{t_roi:.2f}%"
            })
            
    pd.DataFrame(thresh_data).to_csv("scientific_audit/confidence_threshold_analysis.csv", index=False)
    print("Betting & Threshold Audit complete.")

if __name__ == "__main__":
    run_betting_audit()
