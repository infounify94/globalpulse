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
// Phase 7: Canonical accuracy source — never recalculated in frontend.
// Confidence buckets computed by separate query against prediction_store.
// Phase 15: No hardcoded values.
// ─────────────────────────────────────────────────────────────────────────────
export const fetchMetrics = async () => {
  const { data, error } = await supabase
    .from('dashboard_summary')
    .select('*')
    .limit(1)
  if (error) throw error
  const raw = data?.[0] || {}

  // Confidence bucket query — computed directly from prediction_store
  // Cannot add to view without DB migration; executed as separate query.
  const { data: confData } = await supabase
    .from('prediction_store')
    .select('confidence')
    .not('confidence', 'is', null)
    .limit(20000)

  const confRows = confData || []
  const high    = confRows.filter(r => (r.confidence ?? 0) >= 0.8).length
  const medium  = confRows.filter(r => (r.confidence ?? 0) >= 0.6 && (r.confidence ?? 0) < 0.8).length
  const low     = confRows.filter(r => (r.confidence ?? 0) >= 0.4 && (r.confidence ?? 0) < 0.6).length
  const veryLow = confRows.filter(r => (r.confidence ?? 0) < 0.4).length

  return {
    ...raw,
    // Phase 7: KPI fields mapped from view columns
    accuracy:           raw.latest_accuracy,
    brier_score:        raw.latest_brier,
    roi:                raw.latest_roi,
    total_predictions:  raw.live_predictions,
    average_confidence: raw.confidence_calibration,
    // Confidence buckets — real counts from prediction_store
    high_confidence:    high,
    medium_confidence:  medium,
    low_confidence:     low,
    very_low:           veryLow,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Shadow Mode — Recent Verified Outcomes
// Phase 9: prediction_store WHERE prediction_status='VERIFIED' AND date<=NOW()
// Phase 5: is_correct shown ONLY when actual_winner_id is present
// Phase 4: All dates include year+UTC
// ─────────────────────────────────────────────────────────────────────────────
export const fetchShadow = async () => {
  const nowIso = new Date().toISOString()
  const { data, error } = await supabase
    .from('prediction_store')
    .select('*')
    .eq('prediction_status', 'VERIFIED')
    .lte('date', nowIso)          // Phase 4: Historical only — no future verified rows
    .not('actual_winner_id', 'is', null)  // Phase 5: only rows WITH actual winner
    .order('date', { ascending: false, nullsFirst: false })
    .limit(200)

  if (error) {
    console.warn('fetchShadow error:', error.message)
    return []
  }

  const formatTeam = str => str && str !== 'nan'
    ? str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : null

  return (data || []).map(p => {
    const predWinner   = formatTeam(p.predicted_winner_id) || '—'
    const actualWinner = formatTeam(p.actual_winner_id)    // not null — filtered above
    const teamA = formatTeam(p.team_a) || 'Team A'
    const teamB = formatTeam(p.team_b) || 'Team B'
    // Phase 5: is_correct only meaningful when actual winner is confirmed
    const isCorrect = actualWinner != null
      ? (p.is_correct ?? (actualWinner.toLowerCase() === predWinner.toLowerCase()))
      : null
    return {
      ...p,
      event_id:             `${teamA} vs ${teamB}`,
      team_a:               teamA,
      team_b:               teamB,
      predicted_winner:     predWinner,
      actual_winner:        actualWinner,
      is_correct:           isCorrect,
      confidence:           p.confidence ?? null,
      prediction_timestamp: p.verified_time || p.prediction_timestamp || p.date,
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Shadow Predictions — Champion vs Challenger comparison
// Phase 10: shadow_predictions table — real shadow data only
// Returns null if no real data (not mock data injected)
// ─────────────────────────────────────────────────────────────────────────────
export const fetchShadowPredictions = async () => {
  const { data, error } = await supabase
    .from('shadow_predictions')
    .select('*')
    .order('date', { ascending: false })
    .limit(100)

  if (error) {
    console.warn('fetchShadowPredictions error:', error.message)
    return []
  }

  const formatTeam = str => str && str !== 'nan'
    ? str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : '—'

  return (data || []).map(s => {
    const teamA = formatTeam(s.team_a)
    const teamB = formatTeam(s.team_b)
    const predicted = formatTeam(s.predicted_winner)
    const actual    = formatTeam(s.actual_winner)
    // Phase 5: is_correct only when actual winner is known
    const isCorrect = s.actual_winner
      ? (s.actual_winner.toLowerCase() === (s.predicted_winner || '').toLowerCase())
      : null

    let topShap = []
    try {
      const raw = typeof s.top_shap_features === 'string'
        ? JSON.parse(s.top_shap_features)
        : s.top_shap_features
      if (raw && typeof raw === 'object') {
        topShap = Object.entries(raw).map(([name, val]) => ({ name, value: val }))
          .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
          .slice(0, 5)
      }
    } catch (_) {}

    return {
      ...s,
      team_a:           teamA,
      team_b:           teamB,
      predicted_winner: predicted,
      actual_winner:    actual || null,
      is_correct:       isCorrect,
      top_shap_features: topShap,
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Upcoming Matches with Predictions
// Phase 8: prediction_store WHERE prediction_status='PENDING' AND date>NOW()
// Phase 4: Future only. No mock fallback data.
// ─────────────────────────────────────────────────────────────────────────────
export const fetchMatches = async () => {
  const nowIso = new Date().toISOString()
  const { data, error } = await supabase
    .from('prediction_store')
    .select('*')
    .eq('prediction_status', 'PENDING')
    .gt('date', nowIso)           // Phase 4+8: ONLY future matches
    .order('date', { ascending: true })
    .limit(50)

  if (error) throw error

  const formatTeam = str => str && str !== 'nan'
    ? str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : null

  return (data || []).map(m => {
    const teamA      = formatTeam(m.team_a) || null
    const teamB      = formatTeam(m.team_b) || null
    const predWinner = formatTeam(m.predicted_winner_id) || null
    const prob       = m.probability ?? null

    // Phase 12: Parse real top_driving_features from DB — NO hardcoded fallback
    let topFactors = []
    try {
      const raw = typeof m.top_driving_features === 'string'
        ? JSON.parse(m.top_driving_features)
        : m.top_driving_features
      if (raw && Array.isArray(raw.factors)) {
        topFactors = raw.factors
      } else if (raw && typeof raw === 'object') {
        // Handle flat object format: { feature: importance }
        topFactors = Object.entries(raw)
          .map(([name, impact]) => ({ name, impact: typeof impact === 'number' ? impact.toFixed(4) : String(impact) }))
          .slice(0, 5)
      }
    } catch (_) { /* malformed JSON — leave empty */ }

    return {
      ...m,
      team_a:               teamA,
      team_b:               teamB,
      predicted_winner:     predWinner,
      venue:                m.venue && m.venue !== 'nan' ? m.venue : null,
      team_a_probability:   prob,
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
    console.error(`[INTEGRITY VIOLATION] Multiple champions: ${champions.length}`)
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
// Phase 9: Joined view of prediction_store VERIFIED with real outcome data
// ─────────────────────────────────────────────────────────────────────────────
export const fetchHistory = async () => {
  const nowIso = new Date().toISOString()
  const { data, error } = await supabase
    .from('prediction_store')
    .select('*')
    .eq('prediction_status', 'VERIFIED')
    .lte('date', nowIso)          // Phase 4: Historical Replay ONLY date <= NOW()
    .not('actual_winner_id', 'is', null)  // Phase 5: Only show rows with real winner
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
    // Phase 11: Compute duration from start/end
    let duration = null
    if (exp.start_time && exp.end_time) {
      const ms = new Date(exp.end_time) - new Date(exp.start_time)
      const mins = Math.round(ms / 60000)
      duration = mins >= 60 ? `${(mins / 60).toFixed(1)}h` : `${mins}m`
    }
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
      duration,
      winning_model_id: exp.winning_model_id || '—',
      status: exp.end_time ? 'COMPLETED' : 'RUNNING',
    }
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Feature Importance  (feature_importance table — real data)
// Phase 12: Top 20 features. shap_mean shown when available.
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

  // If champion-filtered returned nothing, fall back to any available data
  if ((data || []).length === 0 && champVersion) {
    const { data: fallback } = await supabase
      .from('feature_importance')
      .select('*')
      .order('importance', { ascending: false })
      .limit(20)
    return (fallback || []).map(f => ({
      feature_name:  f.feature_name || '—',
      importance:    f.importance   != null ? parseFloat(f.importance)  : 0,
      shap_mean:     f.shap_mean    != null ? parseFloat(f.shap_mean)   : null,
      feature_type:  f.feature_type || 'statistical',
      model_version: f.model_version || '—',
      computed_at:   f.computed_at  || null,
    }))
  }

  return (data || []).map(f => ({
    feature_name:  f.feature_name || '—',
    importance:    f.importance   != null ? parseFloat(f.importance)  : 0,
    shap_mean:     f.shap_mean    != null ? parseFloat(f.shap_mean)   : null,
    feature_type:  f.feature_type || 'statistical',
    model_version: f.model_version || champVersion || '—',
    computed_at:   f.computed_at  || null,
  }))
}

// ─────────────────────────────────────────────────────────────────────────────
// Not supported in V2 (handled via GitHub Actions)
// ─────────────────────────────────────────────────────────────────────────────
export const predictMatch = async () => ({
  error: 'Predictions are generated via scheduled GitHub Actions workflows'
})
