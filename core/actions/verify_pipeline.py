import os
import sys
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://qzmojqtejmdowkdctlxm.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6bW9qcXRlam1kb3drZGN0bHhtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzQyODgwNCwiZXhwIjoyMDk5MDA0ODA0fQ.SBOA0gNLvMLNJGW13fSS8uj8tb7KLvrbbUBDfSnNYUM"))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CHECKS_PASSED = 0
CHECKS_FAILED = 0


def check(name: str, condition: bool, details: str = ""):
    global CHECKS_PASSED, CHECKS_FAILED
    if condition:
        logging.info(f"  ✓ {name}" + (f" | {details}" if details else ""))
        CHECKS_PASSED += 1
    else:
        logging.error(f"  ✗ {name}" + (f" | {details}" if details else ""))
        CHECKS_FAILED += 1


def run():
    global CHECKS_PASSED, CHECKS_FAILED
    logging.info("--- STARTING PIPELINE HEALTH VERIFICATION ---")

    # 1. Champion exists and has required fields
    res = supabase.table("model_registry").select("*").eq("is_champion", True).execute()
    check("Champion exists in model_registry", len(res.data) > 0)
    if res.data:
        c = res.data[0]
        check("Champion has storage_path", bool(c.get("storage_path")), c.get("storage_path", "MISSING"))
        check("Champion has algorithm", bool(c.get("algorithm")), c.get("algorithm", "MISSING"))
        check("Champion has performance_metrics", bool(c.get("performance_metrics")))
        check("Champion is_champion=True", c.get("is_champion") is True)

        # 2. Validate model file in storage
        storage_path = c.get("storage_path")
        if storage_path:
            try:
                model_data = supabase.storage.from_("models").download(storage_path)
                check("Champion model file downloadable from storage", True, f"{len(model_data)} bytes")
            except Exception as e:
                check("Champion model file downloadable from storage", False, str(e))

    # 3. Check Predictions Exist (any status)
    pred_res = supabase.table("prediction_store").select("id", count="exact").execute()
    check("prediction_store has rows", (pred_res.count or 0) > 0, f"count={pred_res.count}")

    # 4. Check PENDING predictions (OK if 0 — means verify just ran successfully)
    pending_res = supabase.table("prediction_store").select("id", count="exact").eq("prediction_status", "PENDING").execute()
    # Not a hard failure if 0 pending — predict workflow will add more on next run
    logging.info(f"  [INFO] PENDING predictions: {pending_res.count} (0 = verify just completed, next predict will add more)")

    # 4. Shadow predictions exist
    shadow_res = supabase.table("shadow_predictions").select("id", count="exact").execute()
    check("shadow_predictions has rows", (shadow_res.count or 0) > 0, f"count={shadow_res.count}")

    # 5. Dashboard summary populated
    ds_res = supabase.table("dashboard_summary").select("*").limit(1).execute()
    check("dashboard_summary has a row", len(ds_res.data) > 0)
    if ds_res.data:
        ds = ds_res.data[0]
        check("dashboard_summary.latest_accuracy is set", ds.get("latest_accuracy") is not None, str(ds.get("latest_accuracy")))
        check("dashboard_summary.champion is set", bool(ds.get("champion")), ds.get("champion", "MISSING"))

    # 6. Training runs exist
    tr_res = supabase.table("training_runs").select("run_id", count="exact").execute()
    check("training_runs has rows", (tr_res.count or 0) > 0, f"count={tr_res.count}")

    # 7. System health
    sh_res = supabase.table("system_health").select("*").limit(1).execute()
    check("system_health has a row", len(sh_res.data) > 0)

    # 8. Events exist
    ev_res = supabase.table("events").select("id", count="exact").execute()
    check("events table has rows", (ev_res.count or 0) > 0, f"count={ev_res.count}")

    # ── Update system_health ──────────────────────────────────────────────
    import datetime
    supabase.table("system_health").update({
        "last_github_action": datetime.datetime.utcnow().isoformat(),
    }).eq("uptime", "100%").execute()

    # ── Final result ────────────────────────────────────────────────────────
    total = CHECKS_PASSED + CHECKS_FAILED
    logging.info(f"\n{'='*50}")
    logging.info(f"PIPELINE VERIFICATION: {CHECKS_PASSED}/{total} checks passed")
    if CHECKS_FAILED > 0:
        logging.error(f"{CHECKS_FAILED} checks FAILED — see errors above")
        sys.exit(1)
    else:
        logging.info("ALL CHECKS PASSED — PIPELINE IS HEALTHY ✓")


if __name__ == "__main__":
    run()
