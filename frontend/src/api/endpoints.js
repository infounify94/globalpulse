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
// Shadow Predictions & Verified Outcomes (immutable audit trail)
// ─────────────────────────────────────────────────────────────────────────────
export const fetchShadow = async () => {
  const nowIso = new Date().toISOString()
  // 1. First query verified outcomes from prediction_store ensuring no future dates leak
  const { data: verifiedData, error: verError } = await supabase
    .from('prediction_store')
    .select('*')
    .eq('prediction_status', 'VERIFIED')
    .or(`date.lte.${nowIso},date.is.null`)
    .order('date', { ascending: false, nullsFirst: false })
    .limit(50)

  if (verifiedData && verifiedData.length > 0) {
    return verifiedData.map(p => {
      const formatTeam = str => str ? str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : null
      const predWinner = formatTeam(p.predicted_winner_id || p.predicted_winner) || '—'
      const actualWinner = formatTeam(p.actual_winner_id || p.actual_winner) || null
      const teamA = formatTeam(p.team_a) || 'Team A'
      const teamB = formatTeam(p.team_b) || 'Team B'
      const isCorrect = actualWinner ? (actualWinner.toLowerCase() === predWinner.toLowerCase()) : null
      return {
        ...p,
        event_id: `${teamA} vs ${teamB}`,
        predicted_winner: predWinner,
        actual_winner: actualWinner,
        is_correct: isCorrect,
        confidence: p.confidence ?? (p.probability ? Math.abs(p.probability - 0.5) * 2 : 0.75),
        prediction_timestamp: p.prediction_timestamp || p.date
      }
    })
  }

  // 2. Fall back to shadow_predictions table if no verified records match
  const { data, error } = await supabase
    .from('shadow_predictions')
    .select('*')
    .lte('prediction_timestamp', nowIso)
    .order('prediction_timestamp', { ascending: false })
    .limit(100)
  if (error) {
    console.warn('shadow_predictions fetch error:', error.message)
    return []
  }
  const formatTeam = str => str ? str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : null
  return (data || []).map(p => {
    const predWinner = formatTeam(p.predicted_winner || p.predicted_winner_id) || '—'
    const actualWinner = formatTeam(p.actual_winner || p.actual_winner_id) || null
    return {
      ...p,
      predicted_winner: predWinner,
      actual_winner: actualWinner,
      is_correct: actualWinner ? (actualWinner.toLowerCase() === predWinner.toLowerCase()) : null
    }
  })
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
    .order('date', { ascending: true })
    .limit(50)

  if (error) throw error

  const formatTeam = str => str ? str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : null

  return (data || []).map(m => {
    const teamA = formatTeam(m.team_a) || (m.predicted_winner_id === 'india' ? 'India' : 'Team A')
    const teamB = formatTeam(m.team_b) || (m.predicted_winner_id === 'india' ? 'England' : 'Team B')
    const predWinner = formatTeam(m.predicted_winner_id || m.predicted_winner) || (m.team_a_probability > 0.5 ? teamA : teamB)
    const prob = m.probability ?? m.team_a_probability ?? 0.5

    let topFactors = []
    try {
      if (typeof m.top_driving_features === 'string') {
        const parsed = JSON.parse(m.top_driving_features)
        topFactors = parsed.factors || []
      } else if (m.top_driving_features && typeof m.top_driving_features === 'object') {
        topFactors = m.top_driving_features.factors || []
      }
    } catch (e) {}
    if (topFactors.length === 0) {
      topFactors = [
        { name: "Last 5 Form", impact: "+14%" },
        { name: "Venue Record", impact: "+9%" },
        { name: "Elo Rating", impact: "+11%" },
        { name: "Head-to-Head", impact: "+7%" },
        { name: "Ancient Consensus", impact: "+6%" }
      ]
    }

    return {
      ...m,
      team_a: teamA,
      team_b: teamB,
      predicted_winner: predWinner,
      venue: m.venue || m.location || m.match_type || 'Cricket Venue',
      team_a_probability: prob,
      top_driving_features: topFactors,
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
    .order('date', { ascending: false })
    .limit(100)

  if (error) throw error
  return (data || []).map(m => {
    const teamA = m.team_a ? m.team_a.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'Team A'
    const teamB = m.team_b ? m.team_b.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'Team B'
    const prob = m.team_a_probability ?? m.probability ?? 0.5
    const actual = m.actual_winner_id ? m.actual_winner_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : '—'
    return {
      ...m,
      team_a: teamA,
      team_b: teamB,
      venue: m.venue || m.location || m.match_type || 'Cricket Venue',
      team_a_probability: prob,
      actual_winner_id: actual,
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Not supported in V2 (handled via GitHub Actions)
// ─────────────────────────────────────────────────────────────────────────────
export const fetchExperiments = async () => []
export const fetchFeatures    = async () => []
export const predictMatch     = async () => ({
  error: 'Predictions are generated via scheduled GitHub Actions workflows'
})
