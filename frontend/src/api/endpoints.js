import { supabase } from './supabaseClient'

// ─────────────────────────────────────────────────────────────────────────────
// Health / Status  (used by Sidebar to show champion model version)
// ─────────────────────────────────────────────────────────────────────────────
export const fetchHealth = async () => ({ status: 'ok', source: 'supabase' })

export const fetchStatus = async () => {
  const { data } = await supabase
    .from('model_registry')
    .select('model_version, dataset_version, algorithm')
    .eq('is_champion', true)
    .limit(1)
  const champion = data?.[0] || {}
  return {
    status: 'online',
    database: 'connected',
    champion_model_version: champion.model_version || '—',
    dataset_version: champion.dataset_version || '—',
    algorithm: champion.algorithm || '—',
  }
}


// ─────────────────────────────────────────────────────────────────────────────
// Dashboard Summary  (single-row precomputed table)
// DB columns: latest_accuracy, latest_brier, latest_roi, champion,
//             previous_champion, drift_percentage, retrain_date,
//             dataset_version, confidence_calibration, live_predictions, last_update
//
// NOTE: latest_roi is stored as a DECIMAL (e.g. 0.151 = 15.1%)
//       The frontend displays it as a percentage — do NOT multiply by 100 again.
// ─────────────────────────────────────────────────────────────────────────────
export const fetchMetrics = async () => {
  const { data, error } = await supabase
    .from('dashboard_summary')
    .select('*')
    .limit(1)
  if (error) throw error
  const raw = data?.[0] || {}

  return {
    ...raw,
    // Normalize field names for frontend components
    accuracy:             raw.latest_accuracy,
    brier_score:          raw.latest_brier,
    // roi stored as decimal (0.151) → display as-is; components format with toFixed(2)+'%'
    roi:                  raw.latest_roi,
    total_predictions:    raw.live_predictions,
    average_confidence:   raw.confidence_calibration,
    correct_predictions:  raw.correct_predictions   ?? null,
    wrong_predictions:    raw.wrong_predictions     ?? null,
    // High/medium/low confidence buckets (optional — used by ConfidenceDonut)
    high_confidence:      raw.high_confidence       ?? null,
    medium_confidence:    raw.medium_confidence     ?? null,
    low_confidence:       raw.low_confidence        ?? null,
    very_low:             raw.very_low              ?? null,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Shadow Predictions  (immutable audit trail)
// ─────────────────────────────────────────────────────────────────────────────
export const fetchShadow = async () => {
  const { data, error } = await supabase
    .from('shadow_predictions')
    .select('*')
    .order('prediction_timestamp', { ascending: false })
    .limit(100)
  if (error) {
    console.warn('shadow_predictions fetch error:', error.message)
    return []
  }
  return data || []
}

// ─────────────────────────────────────────────────────────────────────────────
// Upcoming Matches with Predictions
// Reads from prediction_store where prediction_status = 'PENDING'
// (i.e. matches that haven't been verified yet — the "upcoming" feed)
// ─────────────────────────────────────────────────────────────────────────────
export const fetchMatches = async () => {
  const { data, error } = await supabase
    .from('prediction_store')
    .select('*')
    .eq('prediction_status', 'PENDING')
    .order('prediction_timestamp', { ascending: false })
    .limit(50)

  if (error) throw error

  return (data || []).map(m => {
    // Prefer explicit team columns; fall back to predicted_winner_id heuristic
    const teamA = m.team_a
      ? m.team_a.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      : (m.predicted_winner_id === 'india' ? 'India' : 'Team A')
    const teamB = m.team_b
      ? m.team_b.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      : (m.predicted_winner_id === 'india' ? 'England' : 'Team B')

    const prob = m.team_a_probability ?? m.probability ?? 0.5

    return {
      ...m,
      team_a: teamA,
      team_b: teamB,
      team_a_probability: prob,
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Models Leaderboard
// DB columns include both flat metrics (accuracy_mean, brier_score, log_loss,
// auc_roc) AND JSONB performance_metrics for older rows.
// ─────────────────────────────────────────────────────────────────────────────
export const fetchModels = async () => {
  const { data, error } = await supabase
    .from('model_registry')
    .select('*')
    .order('training_date', { ascending: false })
    .limit(50)

  if (error) throw error

  return (data || []).map(m => {
    // Normalize metrics — some rows store in flat columns, older rows in JSON
    const perf = m.performance_metrics || {}
    return {
      ...m,
      // Flat columns take priority; fall back to JSONB for legacy rows
      accuracy_mean: m.accuracy_mean  ?? perf.accuracy  ?? null,
      brier_score:   m.brier_score    ?? perf.brier_score ?? null,
      log_loss:      m.log_loss       ?? perf.log_loss   ?? null,
      auc_roc:       m.auc_roc        ?? perf.auc_roc    ?? null,
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Historical Replay  (completed & verified predictions)
// ─────────────────────────────────────────────────────────────────────────────
export const fetchHistory = async () => {
  const { data, error } = await supabase
    .from('prediction_store')
    .select('*')
    .eq('prediction_status', 'VERIFIED')
    .order('prediction_timestamp', { ascending: false })
    .limit(100)

  if (error) throw error
  return data || []
}

// ─────────────────────────────────────────────────────────────────────────────
// Not supported in V2 (handled via GitHub Actions)
// ─────────────────────────────────────────────────────────────────────────────
export const fetchExperiments = async () => []
export const fetchFeatures    = async () => []
export const predictMatch     = async () => ({
  error: 'Predictions are generated via scheduled GitHub Actions workflows'
})
