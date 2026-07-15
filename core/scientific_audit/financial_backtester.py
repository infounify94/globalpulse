import pandas as pd
import numpy as np
from typing import Dict

class FinancialBacktester:
    def __init__(self, initial_bankroll: float = 10000.0, base_bet: float = 100.0):
        self.initial_bankroll = initial_bankroll
        self.base_bet = base_bet
        # Simulated odds (1.90 is standard 5% bookie margin for an even match)
        self.odds = 1.90
        self.b = self.odds - 1.0  # net fractional odds

    def run_backtest(self, y_true: np.ndarray, y_pred_proba: np.ndarray):
        print("\n==================================================")
        print("FINANCIAL QA BACKTESTER (₹)")
        print("==================================================")
        print(f"Starting Bankroll: ₹{self.initial_bankroll:,.2f}")
        print(f"Simulated Odds: {self.odds} (Implied Probability: {1/self.odds:.2%})")
        
        thresholds = [0.55, 0.60, 0.65, 0.70, 0.75]
        strategies = ['Flat_100', '1_Percent', 'Half_Kelly', 'Full_Kelly']
        
        results = []

        for thresh in thresholds:
            for strat in strategies:
                res = self._simulate_strategy(y_true, y_pred_proba, thresh, strat)
                results.append(res)
                
        df_results = pd.DataFrame(results)
        
        # Format the output beautifully
        print("\n--- FINANCIAL TEAR SHEET ---")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        # Sort by ROI descending
        df_results = df_results.sort_values(by='ROI (%)', ascending=False).reset_index(drop=True)
        print(df_results.to_string(index=False))
        
        print("\n==================================================")
        return df_results

    def _simulate_strategy(self, y_true: np.ndarray, y_pred_proba: np.ndarray, threshold: float, strategy: str) -> Dict:
        bankroll = self.initial_bankroll
        peak_bankroll = bankroll
        max_drawdown = 0.0
        
        bets_won = 0
        bets_lost = 0
        total_staked = 0.0
        
        for actual, prob in zip(y_true, y_pred_proba):
            # Only bet if the model has high confidence
            if prob >= threshold:
                # Calculate bet size based on strategy
                if strategy == 'Flat_100':
                    stake = self.base_bet
                elif strategy == '1_Percent':
                    stake = bankroll * 0.01
                elif strategy in ['Full_Kelly', 'Half_Kelly']:
                    # Kelly Formula: f = p - (q/b)
                    p = prob
                    q = 1.0 - p
                    f = p - (q / self.b)
                    
                    if f <= 0:
                        continue # No edge
                        
                    if strategy == 'Half_Kelly':
                        f = f / 2.0
                        
                    stake = bankroll * f
                else:
                    stake = 0
                
                # Prevent betting more than we have
                stake = min(stake, bankroll)
                
                if stake < 1.0:
                    continue # Too broke to bet
                    
                total_staked += stake
                bankroll -= stake
                
                # Outcome
                if actual == 1:
                    winnings = stake * self.odds
                    bankroll += winnings
                    bets_won += 1
                else:
                    bets_lost += 1
                    
                # Track max drawdown
                if bankroll > peak_bankroll:
                    peak_bankroll = bankroll
                else:
                    drawdown = (peak_bankroll - bankroll) / peak_bankroll
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
                        
                if bankroll <= 0:
                    break # Ruin
                    
        profit = bankroll - self.initial_bankroll
        roi = (profit / total_staked) * 100 if total_staked > 0 else 0.0
        win_rate = (bets_won / (bets_won + bets_lost)) * 100 if (bets_won + bets_lost) > 0 else 0.0
        
        return {
            'Strategy': strategy,
            'Threshold': f"{threshold:.0%}",
            'Total Bets': bets_won + bets_lost,
            'Win Rate (%)': f"{win_rate:.1f}%",
            'Total Staked (₹)': f"₹{total_staked:,.0f}",
            'Final Bankroll (₹)': f"₹{bankroll:,.0f}",
            'Net Profit (₹)': f"₹{profit:,.0f}",
            'ROI (%)': round(roi, 2),
            'Max Drawdown (%)': f"{max_drawdown*100:.1f}%"
        }
