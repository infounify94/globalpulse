import os
import sys
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

url = os.environ.get("SUPABASE_URL", "https://placeholder.supabase.co")
key = os.environ.get("SUPABASE_SERVICE_KEY", "placeholder")
supabase: Client = create_client(url, key)

def run():
    logging.info("--- STARTING PIPELINE HEALTH CHECK ---")
    
    # 1. Champion Exists
    res = supabase.table("model_registry").select("*").eq("is_champion", True).execute()
    if not res.data:
        logging.error("PIPELINE FAILED: No Champion model found.")
        sys.exit(1)
        
    # 2. Check Predictions Exist
    res = supabase.table("prediction_store").select("*").limit(1).execute()
    if not res.data:
        logging.error("PIPELINE FAILED: No predictions generated.")
        sys.exit(1)
        
    # 3. Check Shadow Updated
    res = supabase.table("shadow_predictions").select("*").limit(1).execute()
    if not res.data:
        logging.error("PIPELINE FAILED: Shadow mode not updated.")
        sys.exit(1)
        
    # 4. Check Dashboard Metrics
    res = supabase.table("dashboard_summary").select("*").limit(1).execute()
    if not res.data:
        logging.error("PIPELINE FAILED: Dashboard metrics missing.")
        sys.exit(1)

    # 5. Update system_health
    supabase.table("system_health").update({"last_github_action": "now()"}).eq("uptime", "100%").execute()
    logging.info("PIPELINE VERIFIED: SUCCESS")

if __name__ == "__main__":
    run()
