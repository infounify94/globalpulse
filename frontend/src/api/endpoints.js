import { supabase } from './supabaseClient'

// Health
export const fetchHealth = async () => ({ status: 'ok', source: 'supabase' })
export const fetchStatus = async () => ({ status: 'online', database: 'connected' })

// Dashboard Summary (Precomputed)
export const fetchMetrics = async () => {
  const { data, error } = await supabase.from('dashboard_summary').select('*').limit(1)
  if (error) throw error
  return data?.[0] || {}
}
export const fetchShadow = async () => {
  const { data } = await supabase.from('shadow_predictions').select('*').limit(100)
  return data || []
}

// Upcoming matches with predictions (Read from prediction_store where is_correct is null)
export const fetchMatches = async () => {
  const { data, error } = await supabase
    .from('prediction_store')
    .select('*')
    .is('is_correct', null)
    .order('prediction_timestamp', { ascending: false })
    .limit(50)
  
  if (error) throw error
  return data || []
}

// Models leaderboard
export const fetchModels = async () => {
  const { data, error } = await supabase
    .from('model_registry')
    .select('*')
    .order('test_start_year', { ascending: false })
  
  if (error) throw error
  return data || []
}

// Historical replay (Completed predictions)
export const fetchHistory = async () => {
  const { data, error } = await supabase
    .from('prediction_store')
    .select('*')
    .not('is_correct', 'is', null)
    .order('verified_time', { ascending: false })
    .limit(100)
    
  if (error) throw error
  return data || []
}

// Not supported in V2 (Handled via GitHub Actions)
export const fetchExperiments = async () => []
export const fetchFeatures = async () => []
export const predictMatch = async () => ({ error: 'Predictions are generated via scheduled backend jobs' })
