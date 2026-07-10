import { supabase } from './supabaseClient'

// ─────────────────────────────────────────────────────────────────────────────
// Health / Status  (reads from model_registry champion row)
// ─────────────────────────────────────────────────────────────────────────────
export const fetchHealth = async () => ({ status: 'ok', source: 'supabase' })

export const fetchStatus = async () => {
  const { data } = await supabase
    .from('model_registry')
    .select('model_version, dataset_version, algorithm, auc_roc, accuracy_mean, training_date')
    .eq('is_champion', true)
    .limit(1)
  const champion = data?.[0] || {}
  return {
    status: 'online',
    database: 'connected',
    champion_model_version: champion.model_version || '—',
    dataset_version: champion.dataset_version || '—',
    algorithm: champion.algorithm || '—',
    auc_roc: champion.auc_roc || null,
    accuracy_mean: champion.accuracy_mean || null,
    training_date: champion.training_date || null,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard Summary  (reads from dashboard_summary VIEW)
// Backed by: dashboard_snapshots table → dashboard_summary view
// Real computed fields:
//   latest_accuracy = verified correct / verified total  (via fix_production.py)
//   live_predictions = COUNT(*) from prediction_store
//   confidence_calibration = AVG(confidence) from prediction_store
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
    accuracy:           raw.latest_accuracy,
    brier_score:        raw.latest_brier,
    roi:                raw.latest_roi,
    total_predictions:  raw.live_predictions,
    average_confidence: raw.confidence_calibration,
    // confidence buckets are not stored in the view — will show null until backend populates
    high_confidence:    raw.high_confidence   ?? null,
    medium_confidence:  raw.medium_confidence ?? null,
    low_confidence:     raw.low_confidence    ?? null,
    very_low:           raw.very_low          ?? null,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Shadow Mode (recent verified outcomes from prediction_store)
// Phase 9: prediction_store WHERE prediction_status='VERIFIED'
// Joined display fields: team_a, team_b, predicted_winner_id, actual_winner_id,
//   probability, confidence, venue, date, prediction_timestamp
// Phase 5: Wrong badge NEVER shown if actual_winner_id IS NULL
// Phase 4: All dates include year + UTC timezone
// ─────────────────────────────────────────────────────────────────────────────
export const fetchShadow = async () => {
  const nowIso = new Date().toISOString()
  const { data, error } = await supabase
    .from('prediction_store')
    .select('*')
    .eq('prediction_status', 'VERIFIED')
    .lte('date', nowIso)  // Phase 4: Historical only — no future verified rows
    .order('date', { ascending: false, nullsFirst: false })
    .limit(100)

  if (error) {
    console.warn('fetchShadow error:', error.message)
    return []
  }

  const formatTeam = str => str && str !== 'nan'
    ? str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : null

  return (data || []).map(p => {
    const predWinner  = formatTeam(p.predicted_winner_id) || '—'
    const actualWinner = formatTeam(p.actual_winner_id)   || null  // null = Pending, not Wrong
    const teamA = formatTeam(p.team_a) || 'Team A'
    const teamB = formatTeam(p.team_b) || 'Team B'
    // Phase 5: is_correct ONLY when actual winner is known
    const isCorrect = actualWinner != null
      ? (p.is_correct ?? (actualWinner.toLowerCase() === predWinner.toLowerCase()))
      : null
    return {
      ...p,
      event_id:            `${teamA} vs ${teamB}`,
      team_a:              teamA,
      team_b:              teamB,
      predicted_winner:    predWinner,
      actual_winner:       actualWinner,
      is_correct:          isCorrect,
      // confidence stored as 0-1; UI formats as %
      confidence:          p.confidence ?? (p.probability != null ? Math.abs(p.probability - 0.5) * 2 : null),
      prediction_timestamp: p.verified_time || p.prediction_timestamp || p.date,
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Upcoming Matches with Predictions
// Phase 8: prediction_store WHERE prediction_status='PENDING' AND date > NOW()
// Sorted ascending. No mock fallback data.
// ─────────────────────────────────────────────────────────────────────────────
export const fetchMatches = async () => {
  const nowIso = new Date().toISOString()
  const { data, error } = await supabase
    .from('prediction_store')
    .select('*')
    .eq('prediction_status', 'PENDING')
    .gt('date', nowIso)   // Phase 4 + Phase 8: ONLY future matches
    .order('date', { ascending: true })
    .limit(50)

  if (error) throw error

  const formatTeam = str => str && str !== 'nan'
    ? str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : null

  return (data || []).map(m => {
    const teamA     = formatTeam(m.team_a) || null   // null = show as-is, no fabrication
    const teamB     = formatTeam(m.team_b) || null
    const predWinner = formatTeam(m.predicted_winner_id) || null
    const prob      = m.probability ?? null

    // Phase 12: Parse real top_driving_features from DB — NO hardcoded fallback
    let topFactors = []
    try {
      const raw = typeof m.top_driving_features === 'string'
        ? JSON.parse(m.top_driving_features)
        : m.top_driving_features
      if (raw && Array.isArray(raw.factors)) {
        topFactors = raw.factors
      }
    } catch (e) { /* malformed JSON — leave empty */ }
    // Phase 15: No fabricated data. If no real factors exist, show null.

    return {
      ...m,
      team_a:              teamA,
      team_b:              teamB,
      predicted_winner:    predWinner,
      venue:               m.venue && m.venue !== 'nan' ? m.venue : null,
      team_a_probability:  prob,
      top_driving_features: topFactors.length > 0 ? topFactors : null,
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Models Leaderboard  (model_registry)
// Phase 6: Verify only one champion. Show all metrics.
// ─────────────────────────────────────────────────────────────────────────────
export const fetchModels = async () => {
  const { data, error } = await supabase
    .from('model_registry')
    .select('*')
    .order('training_date', { ascending: false })
    .limit(50)

  if (error) throw error

  const champions = (data || []).filter(m => m.is_champion)
  if (champions.length > 1) {
    console.error(`[INTEGRITY VIOLATION] Multiple champions in registry: ${champions.length}`)
  }

  return (data || []).map(m => {
    const perf = m.performance_metrics || {}
    return {
      ...m,
      accuracy_mean: m.accuracy_mean  ?? perf.accuracy    ?? null,
      brier_score:   m.brier_score    ?? perf.brier_score  ?? null,
      log_loss:      m.log_loss       ?? perf.log_loss     ?? null,
      auc_roc:       m.auc_roc        ?? perf.auc_roc      ?? null,
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Historical Replay  (Phase 4+5: verified, past only, no future dates)
// ─────────────────────────────────────────────────────────────────────────────
export const fetchHistory = async () => {
  const nowIso = new Date().toISOString()
  const { data, error } = await supabase
    .from('prediction_store')
    .select('*')
    .eq('prediction_status', 'VERIFIED')
    .lte('date', nowIso)  // Phase 4: Historical Replay ONLY date <= NOW()
    .order('date', { ascending: false })
    .limit(200)

  if (error) throw error

  const formatTeam = str => str && str !== 'nan'
    ? str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : '—'

  return (data || []).map(m => {
    const teamA  = formatTeam(m.team_a)
    const teamB  = formatTeam(m.team_b)
    const actual = formatTeam(m.actual_winner_id)
    const prob   = m.probability ?? m.team_a_probability ?? null

    // Phase 5: is_correct only when actual_winner is real
    const isCorrect = (m.actual_winner_id && m.actual_winner_id !== 'nan')
      ? (m.is_correct ?? (m.actual_winner_id.toLowerCase() === (m.predicted_winner_id || '').toLowerCase()))
      : null

    return {
      ...m,
      team_a:             teamA,
      team_b:             teamB,
      venue:              m.venue && m.venue !== 'nan' ? m.venue : '—',
      team_a_probability: prob,
      actual_winner_id:   actual,
      is_correct:         isCorrect,
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Experiments  (experiment_registry table — real data)
// Phase 11: Show Run ID, Algorithm, Dataset, Metrics. No placeholders.
// ─────────────────────────────────────────────────────────────────────────────
export const fetchExperiments = async () => {
  // Try experiment_registry (the real table found in the audit)
  const { data, error } = await supabase
    .from('experiment_registry')
    .select('*')
    .order('start_time', { ascending: false })
    .limit(50)

  if (error) {
    console.warn('fetchExperiments error:', error.message)
    return []
  }

  // Also fetch model_registry to join winning model info
  const { data: models } = await supabase
    .from('model_registry')
    .select('id, model_version, algorithm, accuracy_mean, brier_score, auc_roc, log_loss, is_champion, training_date')
    .order('training_date', { ascending: false })
    .limit(50)

  const modelMap = {}
  ;(models || []).forEach(m => { modelMap[m.id] = m })

  return (data || []).map(exp => {
    const winningModel = exp.winning_model_id ? modelMap[exp.winning_model_id] : null
    const metrics = exp.metrics_summary || {}
    return {
      id: exp.id,
      algorithm: winningModel?.algorithm || metrics.algorithm || '—',
      dataset_version: exp.dataset_version || '—',
      feature_version: exp.feature_version || '—',
      feature_families: exp.feature_families_tested || [],
      accuracy_mean: winningModel?.accuracy_mean ?? metrics.accuracy ?? null,
      brier_score:   winningModel?.brier_score   ?? metrics.brier    ?? null,
      auc_roc:       winningModel?.auc_roc        ?? metrics.auc     ?? null,
      log_loss:      winningModel?.log_loss       ?? metrics.log_loss ?? null,
      is_champion:   winningModel?.is_champion ?? false,
      start_time:    exp.start_time,
      end_time:      exp.end_time,
      winning_model_id: exp.winning_model_id || '—',
      status:        exp.end_time ? 'COMPLETED' : 'RUNNING',
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Feature Importance  (feature_importance table — real data)
// Phase 12: Top 20 features with importance scores. No empty page.
// ─────────────────────────────────────────────────────────────────────────────
export const fetchFeatures = async () => {
  // First get champion model version
  const { data: champData } = await supabase
    .from('model_registry')
    .select('model_version')
    .eq('is_champion', true)
    .limit(1)
  const champVersion = champData?.[0]?.model_version

  let query = supabase
    .from('feature_importance')
    .select('*')
    .order('importance', { ascending: false })
    .limit(20)

  if (champVersion) {
    query = query.eq('model_version', champVersion)
  }

  const { data, error } = await query

  if (error) {
    console.warn('fetchFeatures error:', error.message)
    return []
  }

  return (data || []).map(f => ({
    feature_name: f.feature_name || '—',
    importance:   f.importance != null ? parseFloat(f.importance) : 0,
    shap_mean:    f.shap_mean  != null ? parseFloat(f.shap_mean)  : null,
    feature_type: f.feature_type || 'statistical',
    model_version: f.model_version || champVersion || '—',
  }))
}

// ─────────────────────────────────────────────────────────────────────────────
// Not supported in V2 (handled via GitHub Actions)
// ─────────────────────────────────────────────────────────────────────────────
export const predictMatch = async () => ({
  error: 'Predictions are generated via scheduled GitHub Actions workflows'
})
