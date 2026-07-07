from sqlalchemy import text
from sqlalchemy.orm import Session

class DataQualityDashboard:
    """
    Diagnostic tool to verify the integrity of the historical data in the ETL pipeline.
    """
    
    def __init__(self, engine):
        self.engine = engine
        
    def run_diagnostics(self):
        """Runs a suite of SQL queries and returns a diagnostic report."""
        report = []
        report.append("=== GlobalPulse Data Quality Dashboard ===")
        
        with Session(self.engine) as session:
            # 1. Total Matches
            total = session.execute(text("SELECT COUNT(*) FROM events")).scalar()
            report.append(f"Total Matches: {total}")
            
            # 2. Missing Venues
            missing_venues = session.execute(
                text("SELECT COUNT(*) FROM events WHERE venue_id IS NULL OR venue_id = ''")
            ).scalar()
            report.append(f"Matches Missing Venue: {missing_venues}")
            
            # 3. Missing Outcomes
            missing_outcomes = session.execute(
                text("SELECT COUNT(*) FROM events WHERE outcome IS NULL")
            ).scalar()
            report.append(f"Matches Missing Outcome: {missing_outcomes}")
            
            # 4. Total Players
            total_players = session.execute(text("SELECT COUNT(*) FROM players")).scalar()
            report.append(f"Total Players: {total_players}")
            
            # 5. Total Features Generated
            total_stats = session.execute(text("SELECT COUNT(*) FROM feature_statistics")).scalar()
            total_astro = session.execute(text("SELECT COUNT(*) FROM feature_astronomy")).scalar()
            report.append(f"Statistical Feature Rows: {total_stats}")
            report.append(f"Astronomy Feature Rows: {total_astro}")
            
            # 6. Duplicate Check (Events on same day at same venue)
            dupes = session.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT date, venue_id, COUNT(*) 
                    FROM events 
                    GROUP BY date, venue_id 
                    HAVING COUNT(*) > 2
                ) as duplicates
            """)).scalar()
            report.append(f"Potential Duplicate Matches (Same Date & Venue > 2): {dupes}")
            
        return "\n".join(report)

if __name__ == "__main__":
    import os
    from core.memory.schema import get_engine
    
    db_url = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse.db")
    engine = get_engine(db_url)
    
    dashboard = DataQualityDashboard(engine)
    print(dashboard.run_diagnostics())
