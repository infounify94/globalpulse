import os
import sqlite3
import pandas as pd
import json

def run_dataset_audit():
    db_path = "globalpulse_dev.db"
    if not os.path.exists(db_path):
        db_path = "../globalpulse_dev.db"
    conn = sqlite3.connect(db_path)
    
    # 1. Check for duplicates in matches table
    query = """
    SELECT e.id, e.date, c.team_a_id, c.team_b_id, e.outcome as winner, v.city as venue
    FROM events e 
    JOIN cricket_match_metadata c ON e.id = c.event_id
    LEFT JOIN venues v ON e.venue_id = v.id
    """
    matches_df = pd.read_sql(query, conn)
    duplicate_ids = matches_df['id'].duplicated().sum()
    duplicate_matches = matches_df.duplicated(subset=['date', 'team_a_id', 'team_b_id']).sum()
    
    dup_report = pd.DataFrame({
        "Check": ["Duplicate Match IDs", "Duplicate Match Combinations (Same Day)"],
        "Count": [duplicate_ids, duplicate_matches],
        "Status": ["PASS" if duplicate_ids == 0 else "FAIL", "PASS" if duplicate_matches == 0 else "FAIL"]
    })
    dup_report.to_csv("scientific_audit/duplicate_report.csv", index=False)
    
    # 2. Data Distribution Drift
    matches_df['year'] = pd.to_datetime(matches_df['date'], format='mixed').dt.year
    drift_report = []
    drift_report.append("# Data Distribution Drift Report\n")
    drift_report.append("Matches per year:")
    yearly_counts = matches_df['year'].value_counts().sort_index()
    drift_report.append(yearly_counts.to_markdown())
    
    drift_report.append("\nTop 5 Venues per Year:")
    for yr in sorted(matches_df['year'].unique()):
        if yr > 2007:
            venues = matches_df[matches_df['year'] == yr]['venue'].value_counts().head(5)
            drift_report.append(f"\n**{yr}**")
            drift_report.append(venues.to_markdown())
            
    with open("scientific_audit/drift_report.md", "w") as f:
        f.write("\n".join(drift_report))
        
    # 3. Dataset Audit Report
    missing_winners = matches_df['winner'].isnull().sum()
    
    report = []
    report.append("# Dataset Audit Report")
    report.append(f"Total Matches: {len(matches_df)}")
    report.append(f"Missing Winners: {missing_winners}")
    report.append(f"Duplicate IDs: {duplicate_ids}")
    report.append(f"Duplicate Matchups on Same Day: {duplicate_matches}")
    
    with open("scientific_audit/dataset_audit_report.md", "w") as f:
        f.write("\n".join(report))
        
    print("Dataset audit complete.")

if __name__ == "__main__":
    run_dataset_audit()
