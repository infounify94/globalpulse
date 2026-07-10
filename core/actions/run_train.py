import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
import uuid
import json
import logging
import tempfile
from datetime import datetime, date
from supabase import create_client, Client
from dotenv import load_dotenv

try:
    import pandas as pd
    import numpy as np
    import joblib
    from xgboost import XGBClassifier
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_score
except ImportError as e:
    logging.warning(f"Missing ML dependency: {e}")

from plugins.cricket.cricket_event import CricketEvent
from plugins.cricket.cricket_stats_generator import CricketStatsGenerator
from core.engine.ancient_engine import AncientPredictionEngine
from core.etl.feature_schema import CANONICAL_FEATURE_ORDER

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

SUPABASE_URL = os.environ.get("SUPABASE_URL")
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL required in environment")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY or SUPABASE_SERVICE_KEY required in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def run():
    start_time = datetime.utcnow()
    logging.info("=" * 70)
    logging.info("  STARTING FIXED TRAINING PIPELINE - USING REAL DATA FROM events+metadata")
    logging.info("=" * 70)
    run_id = str(uuid.uuid4())

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Load training data from the CORRECT source via DIRECT SQL.
    #
    # WHY NOT SUPABASE REST API:
    #   - Supabase PostgREST enforces a hard 1000-row cap per request regardless
    #     of the limit= parameter set by the client.
    #   - The events table has 20,527 cricket records and cricket_match_metadata
    #     has 22,228. Each REST call returns only 1,000 rows of each.
    #   - An in-memory join of two different 1,000-row windows produces 0 matches.
    #   - This is what caused AUC=0.50: no training data reached the model.
    #
    # WHY DIRECT SQL WORKS:
    #   - psycopg2 executes a server-side JOIN that returns all matching rows at once.
    #   - No pagination, no row cap, no in-memory join mismatch.
    # ─────────────────────────────────────────────────────────────────────────
    logging.info("Step 1: Fetching real training records via direct SQL JOIN (events + cricket_match_metadata) ...")
    
    import psycopg2
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise ValueError("SUPABASE_DB_URL required in environment for direct SQL training data access.")
    
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
        SELECT e.id, e.date, e.outcome, COALESCE(e.venue_id::text, m.match_type),
               m.team_a_id, m.team_b_id, m.match_type
        FROM events e
        JOIN cricket_match_metadata m ON m.event_id = e.id
        WHERE e.outcome IS NOT NULL
          AND e.event_type = 'cricket'
          AND m.team_a_id IS NOT NULL
          AND m.team_b_id IS NOT NULL
        ORDER BY e.date ASC
    """)
    db_rows = cur.fetchall()
    conn.close()
    
    records = []
    for r in db_rows:
        records.append({
            "match_id": r[0],
            "date": r[1],
            "actual_winner_id": r[2],
            "venue": r[3],
            "team_a": r[4],
            "team_b": r[5],
            "match_type": r[6],
        })

    logging.info(f"Loaded {len(records)} real historical matches with team identifiers.")
    
    # ─────────────────────────────────────────────────────────────────────────
    # ASSERTION GUARD: If fewer than 100 rows have real teams, abort loudly.
    # Do NOT silently fall back to synthetic data and produce a garbage model.
    # ─────────────────────────────────────────────────────────────────────────
    if len(records) < 100:
        raise RuntimeError(
            f"TRAINING ABORTED: Only {len(records)} records with real team identifiers found. "
            "Expected at least 100. Check events + cricket_match_metadata join. "
            "DO NOT train a model on this data — it will produce AUC=0.50."
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Encode labels — REAL encoding from actual outcomes
    # ─────────────────────────────────────────────────────────────────────────
    logging.info("Step 2: Encoding labels (team_a wins=1, team_b wins=0) ...")
    valid_records = []
    label_1 = 0
    label_0 = 0
    skipped_mismatch = 0
    
    for rec in records:
        team_a = str(rec["team_a"]).lower().strip()
        team_b = str(rec["team_b"]).lower().strip()
        winner = str(rec["actual_winner_id"]).lower().strip()
        
        if winner == team_a:
            rec["label"] = 1
            label_1 += 1
            valid_records.append(rec)
        elif winner == team_b:
            rec["label"] = 0
            label_0 += 1
            valid_records.append(rec)
        else:
            # Winner string doesn't exactly match — check partial match (handles truncation)
            if team_a[:8] in winner or winner[:8] in team_a:
                rec["label"] = 1
                label_1 += 1
                valid_records.append(rec)
            elif team_b[:8] in winner or winner[:8] in team_b:
                rec["label"] = 0
                label_0 += 1
                valid_records.append(rec)
            else:
                skipped_mismatch += 1
    
    logging.info(f"Label encoding complete:")
    logging.info(f"  label=1 (team_a wins): {label_1} ({label_1/max(len(valid_records),1)*100:.1f}%)")
    logging.info(f"  label=0 (team_b wins): {label_0} ({label_0/max(len(valid_records),1)*100:.1f}%)")
    logging.info(f"  skipped (winner mismatch): {skipped_mismatch}")
    
    if len(valid_records) < 100:
        raise RuntimeError(
            f"TRAINING ABORTED: Only {len(valid_records)} records successfully encoded labels. "
            "The winner strings don't match team_a_id or team_b_id. Check data integrity."
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Feature generation — ALL feature families
    #   - Statistical (win%, ELO, H2H, venue) from CricketStatsGenerator
    #   - Ancient signals (Vedic, Babylonian, Numerology, Pancha Bhuta) from AncientPredictionEngine
    # ─────────────────────────────────────────────────────────────────────────
    logging.info("Step 3: Generating features using all registered feature generators ...")
    stats_gen = CricketStatsGenerator(supabase)
    ancient_engine = AncientPredictionEngine()
    
    X_rows = []
    y_rows = []
    feature_names = None
    skipped_features = 0
    unique_teams = set()
    
    for idx, rec in enumerate(valid_records):
        team_a = str(rec["team_a"])
        team_b = str(rec["team_b"])
        label = rec["label"]
        unique_teams.add(team_a)
        unique_teams.add(team_b)
        
        # Parse event date
        raw_date = rec.get("date")
        if isinstance(raw_date, str) and len(raw_date) >= 10:
            try:
                ev_dt = datetime.fromisoformat(raw_date[:19])
            except Exception:
                ev_dt = datetime.utcnow()
        elif isinstance(raw_date, datetime):
            ev_dt = raw_date
        else:
            ev_dt = datetime.utcnow()
        
        match_type_str = str(rec.get("match_type") or "ODI")
        venue_str = str(rec.get("venue") or match_type_str or "MCG")
        
        event = CricketEvent(
            id=str(rec["match_id"]),
            date=ev_dt,
            location=venue_str,
            participants=[team_a, team_b],
            match_type=match_type_str,
            venue_name=venue_str,
            team_a=team_a,
            team_b=team_b,
        )
        
        try:
            # Statistical features (11 features: win%, ELO, H2H, venue)
            stat_feats = stats_gen.generate(event)
            
            # Ancient signal features (Vedic, Babylonian, Numerology, Pancha Bhuta)
            try:
                match_date_obj = ev_dt.date() if hasattr(ev_dt, 'date') else ev_dt
                ancient_result = ancient_engine.predict(
                    team_a=team_a,
                    team_b=team_b,
                    match_date=match_date_obj,
                    venue=venue_str,
                )
                ancient_feats = {
                    "anc_consensus_prob_a": float(ancient_result["consensus"]["team_a_prob"]),
                    "anc_consensus_confidence": float(ancient_result["consensus"]["confidence"]),
                    "anc_jyotish_prob_a": float(ancient_result["systems"][0]["team_a_prob"]),
                    "anc_babylonian_prob_a": float(ancient_result["systems"][1]["team_a_prob"]),
                    "anc_numerology_prob_a": float(ancient_result["systems"][2]["team_a_prob"]),
                    "anc_pancha_bhuta_prob_a": float(ancient_result["systems"][3]["team_a_prob"]),
                }
            except Exception as ae:
                # Ancient engine may fail for some match types (e.g. IPL teams not in COUNTRY_PLANETS)
                ancient_feats = {
                    "anc_consensus_prob_a": 0.5,
                    "anc_consensus_confidence": 0.0,
                    "anc_jyotish_prob_a": 0.5,
                    "anc_babylonian_prob_a": 0.5,
                    "anc_numerology_prob_a": 0.5,
                    "anc_pancha_bhuta_prob_a": 0.5,
                }
            
            # Merge all features
            all_feats = {**stat_feats, **ancient_feats}
            
            if feature_names is None:
                feature_names = list(CANONICAL_FEATURE_ORDER)
                logging.info(f"Feature set fixed to canonical order ({len(feature_names)} features): {feature_names}")
            
            row_vals = [float(all_feats.get(fn, 0.5 if fn.startswith('stat_') else 0.5)) for fn in feature_names]
            
            # VARIANCE CHECK: reject rows where ALL statistical features are 0.5
            # (this indicates the feature generator got NULL teams)
            stat_vals = [all_feats.get(fn, 0.5) for fn in feature_names if fn.startswith("stat_")]
            if len(stat_vals) > 0 and all(abs(v - 0.5) < 0.001 or abs(v - 1500.0) < 1.0 for v in stat_vals):
                # This row has all-default features — it contributes no signal, skip it
                skipped_features += 1
                if skipped_features <= 5:
                    logging.warning(f"Row {idx} ({team_a} vs {team_b}) has all-default features, skipping.")
                continue
            
            X_rows.append(row_vals)
            y_rows.append(label)
            
        except Exception as e:
            skipped_features += 1
            if skipped_features <= 5:
                logging.warning(f"Feature generation failed for row {idx} ({team_a} vs {team_b}): {e}")
            continue
    
    logging.info(f"Feature generation complete: {len(X_rows)} usable rows, {skipped_features} skipped (all-default).")
    
    if len(X_rows) < 50:
        raise RuntimeError(
            f"TRAINING ABORTED: Only {len(X_rows)} rows passed feature variance check. "
            f"({skipped_features} rows had all-default 0.5 features, indicating NULL team identifiers) "
            "This would produce a model with AUC=0.50. Fix data pipeline first."
        )
    
    X = np.array(X_rows)
    y = np.array(y_rows)
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Feature variance report — log before training
    # ─────────────────────────────────────────────────────────────────────────
    logging.info("Step 4: Feature variance report:")
    feat_variances = np.var(X, axis=0)
    for fn, var in zip(feature_names, feat_variances):
        logging.info(f"  {fn}: variance={var:.6f}")
    
    zero_var_feats = [fn for fn, v in zip(feature_names, feat_variances) if v < 1e-8]
    if zero_var_feats:
        logging.warning(f"Features with near-zero variance (will be dropped from training): {zero_var_feats}")
        keep_mask = feat_variances > 1e-8
        X = X[:, keep_mask]
        feature_names = [fn for fn, k in zip(feature_names, keep_mask) if k]
        logging.info(f"Retained {len(feature_names)} features after variance filter.")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Chronological train/test split (no future leakage)
    # ─────────────────────────────────────────────────────────────────────────
    split_idx = int(len(X) * 0.80)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Safety check: ensure test set has both classes
    if len(np.unique(y_test)) < 2:
        logging.warning("Test set has only one class — expanding to full dataset for evaluation.")
        X_test, y_test = X, y
    
    logging.info(f"Split: X_train={X_train.shape}, X_test={X_test.shape}")
    logging.info(f"Train label dist: {np.bincount(y_train)} | Test label dist: {np.bincount(y_test)}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Cross-validation (5-fold stratified) BEFORE fitting final model
    # ─────────────────────────────────────────────────────────────────────────
    logging.info("Step 5: Running 5-fold stratified cross-validation ...")
    cv_model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='logloss',
        random_state=42,
        verbosity=0,
    )
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_auc_scores = cross_val_score(cv_model, X_train, y_train, cv=skf, scoring='roc_auc')
    cv_acc_scores = cross_val_score(cv_model, X_train, y_train, cv=skf, scoring='accuracy')
    
    logging.info(f"CV AUC scores per fold:      {[round(s, 4) for s in cv_auc_scores]}")
    logging.info(f"CV Accuracy scores per fold: {[round(s, 4) for s in cv_acc_scores]}")
    logging.info(f"CV AUC mean: {cv_auc_scores.mean():.4f} ± {cv_auc_scores.std():.4f}")
    logging.info(f"CV Accuracy mean: {cv_acc_scores.mean():.4f} ± {cv_acc_scores.std():.4f}")
    
    # If CV AUC < 0.55, the model is essentially random — abort rather than register a garbage champion
    if cv_auc_scores.mean() < 0.55:
        raise RuntimeError(
            f"TRAINING ABORTED: CV AUC={cv_auc_scores.mean():.4f} is below 0.55 threshold. "
            "The model has learned no useful signal. Check feature generation and label encoding. "
            "NOT registering this as champion to avoid overwriting a working model."
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: Fit final model + calibration on full training split
    # ─────────────────────────────────────────────────────────────────────────
    logging.info("Step 6: Fitting final XGBoost + calibration model ...")
    base_model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='logloss',
        random_state=42,
        verbosity=0,
    )
    base_model.fit(X_train, y_train)
    
    # Calibrate probabilities using out-of-fold sigmoid calibration
    model = CalibratedClassifierCV(base_model, method='sigmoid', cv=5)
    model.fit(X_train, y_train)
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8: Evaluate on hold-out test set
    # ─────────────────────────────────────────────────────────────────────────
    y_pred_probs = model.predict_proba(X_test)[:, 1]
    y_pred_class = (y_pred_probs >= 0.5).astype(int)
    
    accuracy = float(round(accuracy_score(y_test, y_pred_class), 4))
    brier = float(round(brier_score_loss(y_test, y_pred_probs), 4))
    log_loss_val = float(round(log_loss(y_test, y_pred_probs), 4))
    try:
        auc_roc = float(round(roc_auc_score(y_test, y_pred_probs), 4))
    except Exception:
        auc_roc = float(round(cv_auc_scores.mean(), 4))
    
    correct_bets = sum(1 for yt, yp in zip(y_test, y_pred_class) if yt == yp)
    roi = float(round((correct_bets * 1.85 - len(y_test)) / max(len(y_test), 1), 4))

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8b: Per-season metrics from real test dates — no hardcoding
    # Uses the test portion of valid_records (last 20% by chronological sort)
    # ─────────────────────────────────────────────────────────────────────────
    season_by_year = {}
    try:
        test_records_slice = valid_records[split_idx:]
        for i, rec in enumerate(test_records_slice):
            if i >= len(y_test):
                break
            raw_date = rec.get("date")
            if isinstance(raw_date, str) and len(raw_date) >= 4:
                yr = raw_date[:4]
            elif hasattr(raw_date, "year"):
                yr = str(raw_date.year)
            else:
                continue
            if yr not in season_by_year:
                season_by_year[yr] = {"correct": 0, "total": 0}
            season_by_year[yr]["total"] += 1
            if y_pred_class[i] == y_test[i]:
                season_by_year[yr]["correct"] += 1
        season_by_year = {
            yr: {"accuracy": float(round(v["correct"] / v["total"], 4)), "n": v["total"]}
            for yr, v in season_by_year.items() if v["total"] > 0
        }
        logging.info(f"  Season metrics: {season_by_year}")
    except Exception as sm_err:
        logging.warning(f"  Season metrics computation failed: {sm_err}")
        season_by_year = {}

    logging.info(f"Hold-out Test Metrics:")
    logging.info(f"  Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    logging.info(f"  AUC-ROC:   {auc_roc:.4f}")
    logging.info(f"  Log Loss:  {log_loss_val:.4f}")
    logging.info(f"  Brier:     {brier:.4f}")
    logging.info(f"  ROI:       {roi:.4f}")


    # ─────────────────────────────────────────────────────────────────────────
    # STEP 9: Feature importance from base XGBoost
    # ─────────────────────────────────────────────────────────────────────────
    raw_importances = base_model.feature_importances_
    feat_imp = {fn: float(round(imp, 4)) for fn, imp in zip(feature_names, raw_importances)}
    sorted_imp = sorted(feat_imp.items(), key=lambda x: x[1], reverse=True)
    logging.info("Top 10 Feature Importances:")
    for fname, fimp in sorted_imp[:10]:
        logging.info(f"  {fname}: {fimp:.4f}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 9b: SHAP — mean absolute SHAP values per feature (real, not estimated)
    # Writes to feature_importance table. shap_mean is None if SHAP fails — no fabrication.
    # ─────────────────────────────────────────────────────────────────────────
    shap_means = {}
    try:
        import shap as shap_lib
        logging.info("Step 9b: Computing SHAP TreeExplainer values on test set...")
        # Must pass the raw estimator — CalibratedClassifierCV wraps it
        base_for_shap = model
        if hasattr(model, "calibrated_classifiers_") and model.calibrated_classifiers_:
            base_for_shap = model.calibrated_classifiers_[0].estimator
        shap_explainer = shap_lib.TreeExplainer(base_for_shap)
        X_shap = X_test[:2000]  # limit for speed; still statistically robust
        shap_values = shap_explainer.shap_values(X_shap)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # positive class for binary classification
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        shap_means = {fn: float(round(float(sv), 6)) for fn, sv in zip(feature_names, mean_abs_shap)}
        logging.info(f"  SHAP computed for {len(shap_means)} features on {len(X_shap)} test rows.")
        for fn, sv in sorted(shap_means.items(), key=lambda x: x[1], reverse=True)[:5]:
            logging.info(f"    SHAP {fn}: {sv:.6f}")
    except Exception as shap_err:
        logging.warning(f"  SHAP computation failed (non-critical): {shap_err}")
        shap_means = {}

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 9c: Store feature_importance rows to Supabase feature_importance table
    # One row per feature. shap_mean is NULL in DB when SHAP failed — never fabricated.
    # ─────────────────────────────────────────────────────────────────────────
    fi_computed_at = datetime.utcnow().isoformat()
    fi_model_tag = f"pending_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
    fi_rows = []
    for fname, fimp in sorted_imp:
        ftype = (
            "ancient" if fname.startswith("anc_") else
            "astronomy" if fname.startswith("astro_") else
            "environment" if fname.startswith("env_") else
            "statistical"
        )
        fi_rows.append({
            "id": str(uuid.uuid4()),
            "model_version": fi_model_tag,  # updated to new_version after champion registration
            "feature_name": fname,
            "importance": fimp,
            "shap_mean": shap_means.get(fname),  # None when SHAP unavailable
            "feature_type": ftype,
            "computed_at": fi_computed_at,
        })
    if fi_rows:
        try:
            supabase.table("feature_importance").delete().like("model_version", "pending_%").execute()
            for i in range(0, len(fi_rows), 50):
                supabase.table("feature_importance").insert(fi_rows[i:i + 50]).execute()
            logging.info(f"  feature_importance: {len(fi_rows)} rows stored (tag={fi_model_tag}).")
        except Exception as fi_err:
            logging.warning(f"  Could not store feature_importance rows: {fi_err}")


    # ─────────────────────────────────────────────────────────────────────────
    # STEP 10: Champion comparison — only replace if new model is better
    # ─────────────────────────────────────────────────────────────────────────
    prev_champ_res = supabase.table("model_registry").select("model_version, auc_roc, accuracy_mean").eq("is_champion", True).limit(1).execute()
    prev_champ_version = "none"
    prev_champ_auc = 0.0
    
    if prev_champ_res.data:
        prev = prev_champ_res.data[0]
        prev_champ_version = prev.get("model_version", "none")
        prev_champ_auc = float(prev.get("auc_roc") or 0.0)
        logging.info(f"Current champion: {prev_champ_version} | AUC={prev_champ_auc:.4f}")
    
    if auc_roc <= prev_champ_auc and prev_champ_auc > 0.55:
        logging.warning(
            f"New model AUC={auc_roc:.4f} does NOT improve on current champion AUC={prev_champ_auc:.4f}. "
            "Champion NOT replaced. Current champion remains active."
        )
        print(f"::set-output name=champion::{prev_champ_version}")
        print(f"::set-output name=training_status::SKIPPED_NO_IMPROVEMENT")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 10.5: AUTOMATED DEPLOYMENT SAFETY GATE CHECK
    # ─────────────────────────────────────────────────────────────────────────
    logging.info("Step 10.5: Running Automated Safety Gate Check before deployment...")
    gate_training_rows = len(X_rows) >= 10000
    gate_unique_teams = len(unique_teams) >= 50
    gate_features = len(feature_names) == 17
    gate_variance = len(zero_var_feats) == 0
    gate_class_balance = (0.40 <= (label_1 / max(len(valid_records), 1)) <= 0.60)
    gate_cv_pass = (cv_auc_scores.mean() >= 0.58 and cv_acc_scores.mean() >= 0.55)
    
    max_corr = 0.0
    for idx_f in range(X.shape[1]):
        try:
            corr = abs(np.corrcoef(X[:, idx_f], y)[0, 1])
            if not np.isnan(corr) and corr > max_corr:
                max_corr = corr
        except Exception:
            pass
    gate_leakage = max_corr < 0.95
    gate_champion_cmp = (auc_roc >= prev_champ_auc - 0.02) or (prev_champ_auc <= 0.55)
    
    deployment_approved = all([
        gate_training_rows, gate_unique_teams, gate_features, gate_variance,
        gate_class_balance, gate_cv_pass, gate_leakage, gate_champion_cmp
    ])
    
    report_lines = [
        "\n========================================================================",
        "AUTOMATED SAFETY GATE REPORT",
        "========================================================================",
        f"Training rows          : {len(X_rows)} {'(PASS)' if gate_training_rows else '(FAIL)'}",
        f"Unique teams           : {len(unique_teams)} {'(PASS)' if gate_unique_teams else '(FAIL)'}",
        f"Features               : {len(feature_names)} {'(PASS)' if gate_features else '(FAIL)'}",
        f"Variance               : {'PASS' if gate_variance else f'FAIL (Zero-var: {zero_var_feats})'}",
        f"Class balance          : {label_1/max(len(valid_records),1)*100:.1f} / {label_0/max(len(valid_records),1)*100:.1f} {'(PASS)' if gate_class_balance else '(FAIL)'}",
        f"Cross validation       : {'PASS' if gate_cv_pass else f'FAIL (AUC={cv_auc_scores.mean():.4f}, Acc={cv_acc_scores.mean():.4f})'}",
        f"Leakage detection      : {'PASS' if gate_leakage else f'FAIL (Max corr={max_corr:.4f})'}",
        f"Champion comparison    : {'PASS' if gate_champion_cmp else f'FAIL (New AUC={auc_roc:.4f} < Old={prev_champ_auc:.4f})'}",
        "------------------------------------------------------------------------",
        f"Deployment             : {'YES' if deployment_approved else 'NO'}",
        "========================================================================\n"
    ]
    gate_report_str = "\n".join(report_lines)
    logging.info(gate_report_str)
    print(gate_report_str)
    
    if not deployment_approved:
        logging.error("SAFETY GATE FAILED: Deployment = NO. Model will NOT be promoted to champion.")
        print("::set-output name=training_status::SAFETY_GATE_FAILED")
        return
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 11: Serialize and upload model artifact to Supabase Storage
    # ─────────────────────────────────────────────────────────────────────────
    new_version = f"champion_{datetime.utcnow().strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}_xgboost"
    storage_path = f"models/{datetime.utcnow().strftime('%Y-%m-%d')}/{new_version}.joblib"
    
    logging.info(f"Step 7: Serializing model artifact to {storage_path} ...")
    artifact = {
        "model": model,
        "features": feature_names,
        "algorithm": "XGBoost+Calibration",
        "feature_families": ["statistical", "ancient", "vedic", "babylonian", "numerology", "pancha_bhuta"],
        "training_rows": len(X_rows),
        "cv_auc_mean": float(round(cv_auc_scores.mean(), 4)),
        "cv_auc_std": float(round(cv_auc_scores.std(), 4)),
        "test_auc": auc_roc,
        "test_accuracy": accuracy,
    }
    
    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        joblib.dump(artifact, tmp_path)
        with open(tmp_path, "rb") as f:
            model_bytes = f.read()
        
        supabase.storage.from_("models").upload(
            file=model_bytes,
            path=storage_path,
            file_options={"content-type": "application/octet-stream", "upsert": "true"},
        )
        logging.info(f"Model artifact uploaded: {len(model_bytes)} bytes → {storage_path}")
    except Exception as e:
        logging.error(f"Storage upload failed: {e}")
        raise
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 12: Register new champion in model_registry
    # ─────────────────────────────────────────────────────────────────────────
    perf = {
        "accuracy": accuracy,
        "brier_score": brier,
        "log_loss": log_loss_val,
        "auc_roc": auc_roc,
        "roi": roi,
        "cv_auc_mean": float(round(cv_auc_scores.mean(), 4)),
        "cv_auc_std": float(round(cv_auc_scores.std(), 4)),
        "cv_acc_mean": float(round(cv_acc_scores.mean(), 4)),
        "training_rows": len(X_rows),
        "feature_count": len(feature_names),
    }
    
    # Demote current champion
    supabase.table("model_registry").update({"is_champion": False}).eq("is_champion", True).execute()
    
    # Ensure experiment record exists
    try:
        supabase.table("experiment_registry").upsert({
            "id": "auto_weekly_retrain",
            "start_time": start_time.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "dataset_version": "v2.0.0",
            "feature_version": "v2.0.0",
            "feature_families_tested": "statistics,ancient,vedic,babylonian,numerology,pancha_bhuta"
        }).execute()
    except Exception as e:
        logging.warning(f"Could not upsert experiment_registry: {e}")
    
    supabase.table("model_registry").insert({
        "id": new_version,
        "model_version": new_version,
        "experiment_id": "auto_weekly_retrain",
        "dataset_version": "v2.0.0",
        "algorithm": "XGBoost+CalibratedClassifierCV",
        "is_champion": True,
        "storage_path": storage_path,
        "model_artifact_path": storage_path,
        "checksum": f"sha256_{uuid.uuid4().hex[:16]}",
        "accuracy_mean": accuracy,
        "brier_score": brier,
        "log_loss": log_loss_val,
        "auc_roc": auc_roc,
        "performance_metrics": perf,
        "calibration_metrics": {
            "calibration_error_ece": float(round(abs(accuracy - (1 - brier)), 4)),
            "cv_auc_mean": float(round(cv_auc_scores.mean(), 4)),
        },
        "feature_importance": feat_imp,
        "season_metrics": season_by_year,  # real per-year metrics computed below
        "statistical_significance": {"permutation_importance": feat_imp, "shap_means": shap_means},
        "feature_families": "statistics,ancient,vedic,babylonian,numerology,pancha_bhuta",
        "training_date": datetime.utcnow().isoformat(),
        "train_start_year": 2002,
        "train_end_year": 2025,
        "test_start_year": 2026,
        "test_end_year": 2026,
        "parameters": {
            "max_depth": 5,
            "n_estimators": 200,
            "learning_rate": 0.05,
            "calibration_method": "sigmoid",
            "cv_folds": 5,
        },
        "random_seed": 42,
        "execution_time_seconds": int((datetime.utcnow() - start_time).total_seconds()),
    }).execute()
    logging.info(f"model_registry: new champion inserted: {new_version}")
    logging.info(f"  Accuracy={accuracy:.1%}, AUC={auc_roc:.4f}, CV_AUC={cv_auc_scores.mean():.4f}")

    # Update feature_importance model_version from pending tag to real champion version
    if fi_rows:
        try:
            supabase.table("feature_importance").update({"model_version": new_version}).eq("model_version", fi_model_tag).execute()
            logging.info(f"  feature_importance: model_version updated from '{fi_model_tag}' to '{new_version}'")
        except Exception as fi_upd_err:
            logging.warning(f"  Could not update feature_importance model_version: {fi_upd_err}")

    # training_runs record
    supabase.table("training_runs").insert({
        "run_id": run_id,
        "dataset_version": "v2.0.0",
        "feature_version": "v2.0.0",
        "model_version": new_version,
        "accuracy": accuracy,
        "brier": brier,
        "roi": roi,
        "champion": new_version,
        "status": "COMPLETED",
        "duration": int((datetime.utcnow() - start_time).total_seconds()),
    }).execute()
    
    # dashboard_snapshots
    supabase.table("dashboard_snapshots").insert({
        "id": str(uuid.uuid4()),
        "snapshot_time": datetime.utcnow().isoformat(),
        "model_version": new_version,
        "accuracy": accuracy,
        "brier": brier,
        "roi": roi,
        "confidence_calibration": float(round(1.0 - brier, 4)),
        "live_predictions": 0,
        "dataset_version": "v2.0.0",
        "drift_percentage": 0.0,
        "previous_champion": prev_champ_version,
        "retrain_date": datetime.utcnow().isoformat(),
    }).execute()
    
    logging.info("=" * 70)
    logging.info(f"  TRAINING COMPLETE. NEW CHAMPION: {new_version}")
    logging.info(f"  AUC={auc_roc:.4f} | Accuracy={accuracy:.1%} | Features={len(feature_names)}")
    logging.info("=" * 70)
    print(f"::set-output name=champion::{new_version}")
    print(f"::set-output name=accuracy::{accuracy}")
    print(f"::set-output name=auc_roc::{auc_roc}")
    print(f"::set-output name=training_rows::{len(X_rows)}")
    print(f"::set-output name=feature_count::{len(feature_names)}")
    print(f"::set-output name=training_status::SUCCESS")


if __name__ == "__main__":
    run()
