import os
import json
import logging
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    logging.warning("pandas not installed. Automated Reports may fail.")

from core.memory.schema import get_engine

class AutomatedReportingEngine:
    """
    Automatically generates static reports (HTML, PDF, CSV) 
    after every major training or walk-forward cycle.
    Ensures domain-independence by reading generic DB schemas.
    """
    
    def __init__(self, engine, report_dir="reports"):
        self.engine = engine
        self.report_dir = report_dir
        os.makedirs(self.report_dir, exist_ok=True)
        
    def _fetch_experiment_data(self):
        query = """
        SELECT e.id, e.start_time, m.algorithm, m.performance_metrics
        FROM experiment_registry e
        JOIN model_registry m ON e.id = m.experiment_id
        ORDER BY e.start_time DESC LIMIT 10
        """
        try:
            return pd.read_sql(query, self.engine)
        except Exception as e:
            logging.error(f"Failed to fetch experiment data: {e}")
            return pd.DataFrame()
            
    def generate_all(self):
        """Generates HTML and CSV reports (PDF can be generated via HTML export)."""
        df = self._fetch_experiment_data()
        
        if df.empty:
            logging.info("No data to report.")
            return
            
        # Parse metrics safely
        def parse_metric(val, key):
            if isinstance(val, str):
                return float(eval(val).get(key, 0))
            return val.get(key, 0)
            
        df['Accuracy'] = df['performance_metrics'].apply(lambda x: parse_metric(x, 'accuracy'))
        df['Brier'] = df['performance_metrics'].apply(lambda x: parse_metric(x, 'brier_score'))
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # 1. Export CSV
        csv_path = os.path.join(self.report_dir, f"report_{timestamp}.csv")
        df[['id', 'start_time', 'algorithm', 'Accuracy', 'Brier']].to_csv(csv_path, index=False)
        
        # 2. Export HTML
        html_path = os.path.join(self.report_dir, f"report_{timestamp}.html")
        html_content = f"""
        <html>
        <head><title>GlobalPulse Automated Report</title></head>
        <body style="font-family: sans-serif;">
            <h1>GlobalPulse Automated Research Report</h1>
            <p>Generated at: {timestamp} UTC</p>
            {df[['id', 'algorithm', 'Accuracy', 'Brier']].to_html(index=False)}
        </body>
        </html>
        """
        with open(html_path, "w") as f:
            f.write(html_content)
            
        logging.info(f"Automated reports generated at {self.report_dir}/report_{timestamp}.*")
        return {"csv": csv_path, "html": html_path}
