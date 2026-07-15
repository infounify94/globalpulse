"""
GlobalPulse Production Forensic Audit Script
Phases 1-18: Complete database and data integrity audit
"""
import sqlite3
import json
from datetime import datetime, timezone

def run():
    db = sqlite3.connect('globalpulse_dev.db')
    db.row_factory = sqlite3.Row
    c = db.cursor()

    print("=" * 60)
    print("PHASE 1 — DATABASE TABLE INVENTORY")
    print("=" * 60)

    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in c.fetchall()]
    for t in tables:
        c.execute(f"SELECT COUNT(*) FROM [{t}]")
        count = c.fetchone()[0]
        print(f"  {t}: {count} rows")

    print()
    c.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
    views = [r[0] for r in c.fetchall()]
    print(f"VIEWS: {views}")

    print()
    print("=" * 60)
    print("PHASE 3 — PREDICTION_STORE AUDIT")
    print("=" * 60)

    c.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN prediction_status='PENDING' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN prediction_status='VERIFIED' THEN 1 ELSE 0 END) as verified,
            SUM(CASE WHEN team_a IS NULL OR team_a='nan' THEN 1 ELSE 0 END) as null_team_a,
            SUM(CASE WHEN team_b IS NULL OR team_b='nan' THEN 1 ELSE 0 END) as null_team_b,
            SUM(CASE WHEN venue IS NULL OR venue='nan' THEN 1 ELSE 0 END) as null_venue,
            SUM(CASE WHEN date IS NULL THEN 1 ELSE 0 END) as null_date,
            SUM(CASE WHEN probability IS NULL THEN 1 ELSE 0 END) as null_prob,
            SUM(CASE WHEN probability < 0 OR probability > 1 THEN 1 ELSE 0 END) as invalid_prob
        FROM prediction_store
    """)
    r = dict(c.fetchone())
    for k, v in r.items():
        print(f"  {k}: {v}")

    print()
    print("PHASE 4 — DATE INTEGRITY (upcoming = future only)")
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute("""
        SELECT COUNT(*) FROM prediction_store
        WHERE prediction_status='PENDING' AND date <= ?
    """, (now_iso,))
    stale_pending = c.fetchone()[0]
    print(f"  PENDING with past dates (should be 0): {stale_pending}")

    c.execute("""
        SELECT COUNT(*) FROM prediction_store
        WHERE prediction_status='VERIFIED' AND date > ?
    """, (now_iso,))
    future_verified = c.fetchone()[0]
    print(f"  VERIFIED with future dates (should be 0): {future_verified}")

    print()
    print("PHASE 5 — MATCH STATUS VALIDATION")
    c.execute("""
        SELECT COUNT(*) FROM prediction_store
        WHERE is_correct IS NOT NULL AND prediction_status='PENDING'
    """)
    wrong_pending = c.fetchone()[0]
    print(f"  PENDING with is_correct set (should be 0): {wrong_pending}")

    c.execute("""
        SELECT COUNT(*) FROM prediction_store
        WHERE prediction_status='VERIFIED' AND actual_winner_id IS NULL
    """)
    verified_no_winner = c.fetchone()[0]
    print(f"  VERIFIED with no actual_winner (data issue): {verified_no_winner}")

    print()
    print("PHASE 6 — MODEL_REGISTRY AUDIT")
    c.execute("SELECT COUNT(*) FROM model_registry WHERE is_champion=1")
    champ_count = c.fetchone()[0]
    print(f"  Champion count (must be 1): {champ_count}")

    c.execute("SELECT model_version, algorithm, accuracy_mean, brier_score, auc_roc, log_loss, training_date, is_champion FROM model_registry ORDER BY training_date DESC")
    models = [dict(r) for r in c.fetchall()]
    for m in models[:5]:
        print(f"  [{m['model_version'][:20]}] champ={m['is_champion']} acc={m['accuracy_mean']} auc={m['auc_roc']}")

    print()
    print("PHASE 7 — METRIC CONSISTENCY (dashboard_summary view)")
    try:
        c.execute("SELECT * FROM dashboard_summary LIMIT 1")
        row = dict(c.fetchone() or {})
        print(f"  dashboard_summary row: {json.dumps(row, default=str)[:500]}")
    except Exception as e:
        print(f"  dashboard_summary ERROR: {e}")

    print()
    print("PHASE 8 — UPCOMING MATCHES")
    c.execute("""
        SELECT COUNT(*) FROM prediction_store
        WHERE prediction_status='PENDING' AND date > ?
    """, (now_iso,))
    upcoming = c.fetchone()[0]
    print(f"  Future PENDING predictions: {upcoming}")

    c.execute("""
        SELECT team_a, team_b, venue, date, probability, confidence
        FROM prediction_store
        WHERE prediction_status='PENDING' AND date > ?
        ORDER BY date ASC LIMIT 5
    """, (now_iso,))
    rows = [dict(r) for r in c.fetchall()]
    for r in rows:
        print(f"  {r['team_a']} vs {r['team_b']} @ {r['venue']} | {r['date']} | prob={r['probability']}")

    print()
    print("PHASE 9 — RECENT OUTCOMES (VERIFIED)")
    c.execute("""
        SELECT team_a, team_b, predicted_winner_id, actual_winner_id, is_correct, probability, date
        FROM prediction_store
        WHERE prediction_status='VERIFIED'
        ORDER BY date DESC LIMIT 5
    """)
    rows = [dict(r) for r in c.fetchall()]
    for r in rows:
        print(f"  {r['team_a']} vs {r['team_b']} | pred={r['predicted_winner_id']} actual={r['actual_winner_id']} correct={r['is_correct']}")

    print()
    print("PHASE 10 — SHADOW_PREDICTIONS TABLE")
    try:
        c.execute("SELECT COUNT(*) FROM shadow_predictions")
        sp = c.fetchone()[0]
        print(f"  shadow_predictions rows: {sp}")
    except Exception as e:
        print(f"  shadow_predictions ERROR: {e}")

    print()
    print("PHASE 11 — EXPERIMENT_REGISTRY")
    try:
        c.execute("SELECT COUNT(*) FROM experiment_registry")
        er = c.fetchone()[0]
        print(f"  experiment_registry rows: {er}")
        c.execute("SELECT * FROM experiment_registry ORDER BY start_time DESC LIMIT 3")
        rows = [dict(r) for r in c.fetchall()]
        for r in rows:
            print(f"  {r}")
    except Exception as e:
        print(f"  experiment_registry ERROR: {e}")

    print()
    print("PHASE 12 — FEATURE_IMPORTANCE")
    try:
        c.execute("SELECT COUNT(*) FROM feature_importance")
        fi = c.fetchone()[0]
        print(f"  feature_importance rows: {fi}")
        c.execute("SELECT feature_name, importance, shap_mean, model_version FROM feature_importance ORDER BY importance DESC LIMIT 5")
        rows = [dict(r) for r in c.fetchall()]
        for r in rows:
            print(f"  {r['feature_name']}: importance={r['importance']}, shap={r['shap_mean']}, model={r['model_version']}")
    except Exception as e:
        print(f"  feature_importance ERROR: {e}")

    print()
    print("PHASE 13 — PATTERN_MEMORY")
    try:
        c.execute("SELECT COUNT(*) FROM pattern_memory")
        pm = c.fetchone()[0]
        print(f"  pattern_memory rows: {pm}")
    except Exception as e:
        print(f"  pattern_memory ERROR: {e}")

    print()
    print("PHASE 14 — VERIFICATION_LOGS")
    try:
        c.execute("SELECT COUNT(*) FROM verification_logs")
        vl = c.fetchone()[0]
        print(f"  verification_logs rows: {vl}")
    except Exception as e:
        print(f"  verification_logs ERROR: {e}")

    print()
    print("PHASE 17 — DUPLICATE PREDICTION_IDS")
    c.execute("""
        SELECT id, COUNT(*) as cnt FROM prediction_store
        GROUP BY id HAVING cnt > 1
        LIMIT 10
    """)
    dups = c.fetchall()
    print(f"  Duplicate prediction_store IDs: {len(dups)}")

    print()
    print("PRODUCTION HEALTH SUMMARY")
    print("-" * 40)
    issues = []
    if stale_pending > 0:
        issues.append(f"CRITICAL: {stale_pending} PENDING matches with past dates")
    if future_verified > 0:
        issues.append(f"CRITICAL: {future_verified} VERIFIED matches with future dates")
    if champ_count != 1:
        issues.append(f"CRITICAL: {champ_count} champions (must be exactly 1)")
    if verified_no_winner > 0:
        issues.append(f"WARNING: {verified_no_winner} VERIFIED rows with no actual_winner")
    if len(dups) > 0:
        issues.append(f"WARNING: {len(dups)} duplicate IDs in prediction_store")

    if issues:
        for i in issues:
            print(f"  ❌ {i}")
    else:
        print("  ✅ No critical issues found")

    db.close()

if __name__ == '__main__':
    run()
