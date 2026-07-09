import api from './client'

// Health
export const fetchHealth   = () => api.get('/').then(r => r.data)
export const fetchStatus   = () => api.get('/system/status').then(r => r.data)

// Metrics / Shadow
export const fetchMetrics  = () => api.get('/api/shadow_metrics').then(r => r.data)
export const fetchShadow   = () => api.get('/api/shadow_predictions').then(r => r.data)

// Upcoming matches with predictions
export const fetchMatches  = (params) => api.get('/api/matches/upcoming', { params }).then(r => r.data)

// Models leaderboard
export const fetchModels   = () => api.get('/api/models').then(r => r.data)

// Experiments
export const fetchExperiments = () => api.get('/api/experiments').then(r => r.data)

// Feature importance
export const fetchFeatures = () => api.get('/api/features').then(r => r.data)

// Historical replay
export const fetchHistory  = () => api.get('/api/history').then(r => r.data)

// Predict a specific match
export const predictMatch  = (data) => api.post('/predict', data).then(r => r.data)
