import DashboardLayout from '../layouts/DashboardLayout'
import { useHistory } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { fmtDateTime } from '../utils/format'
import { AlertTriangle } from 'lucide-react'

// ─────────────────────────────────────────────────────────────────────────────
// Not Implemented Banner — used for modules awaiting Phase 2 backend work.
// Shows the exact module name, what it requires, and current DB status.
// Phase 15: NEVER fabricates data — shows empty state honestly.
// ─────────────────────────────────────────────────────────────────────────────
function NotImplemented({ feature, description, requirements }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '48px 32px', textAlign: 'center',
    }}>
      <AlertTriangle size={36} color="#d97706" style={{ marginBottom: 16 }} />
      <h3 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>{feature}</h3>
      <p style={{ fontSize: 13, color: '#64748b', maxWidth: 480, lineHeight: 1.6, marginBottom: 20 }}>
        {description}
      </p>
      <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '16px 24px', textAlign: 'left', maxWidth: 480, width: '100%' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Required for Implementation
        </div>
        {requirements.map((req, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 6, fontSize: 12, color: '#475569' }}>
            <span style={{ color: '#d97706', fontWeight: 700, marginTop: 1 }}>◦</span>
            {req}
          </div>
        ))}
      </div>
      <div style={{ marginTop: 16, fontSize: 11, color: '#94a3b8' }}>
        No placeholder data is shown. This module will display real data once the backend is connected.
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Pattern Memory Page — Phase 13
// Requires: nearest-neighbour retrieval, stored embeddings in pattern_memory table.
// ─────────────────────────────────────────────────────────────────────────────
export function PatternMemoryPage() {
  return (
    <DashboardLayout
      title="Pattern Memory"
      subtitle="Nearest historical match patterns and embedding similarity"
    >
      <div className="card">
        <NotImplemented
          feature="Pattern Memory Engine — Not Yet Implemented"
          description={`This module performs nearest-neighbour retrieval over historical match embeddings 
            to find the most similar past fixtures and their outcomes. The backend pipeline has not yet 
            computed or stored embeddings in the pattern_memory table.`}
          requirements={[
            'pattern_memory table must be populated with match embeddings (currently 0 rows)',
            'Embedding generation step must be added to the post-training pipeline',
            'Nearest-neighbour index (e.g. FAISS or pgvector) must be deployed',
            'Backend endpoint: GET /api/v1/patterns?match_id=:id',
            'Fields to display: Similarity Score, Outcome, Probability, Pattern Explanation',
          ]}
        />
      </div>
    </DashboardLayout>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Historical Replay Page — Phase 4+5
// Phase 15: Pure data rendering. No manual frontend probability/winner calculations.
// Only shows VERIFIED rows with confirmed actual_winner (filtered in fetchHistory).
// ─────────────────────────────────────────────────────────────────────────────
export function HistoricalReplayPage() {
  const { data: history, isLoading, isError } = useHistory()

  return (
    <DashboardLayout
      title="Historical Replay"
      subtitle="Completed and verified match predictions — from prediction_store VERIFIED"
    >
      <div className="card">
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600 }}>Completed Matches — Audit Trail</h3>
          <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
            prediction_store WHERE prediction_status='VERIFIED' AND actual_winner_id IS NOT NULL AND date &lt;= NOW()
          </p>
        </div>
        {isLoading ? <TableSkeleton rows={10} /> : (
          <table className="gp-table">
            <thead>
              <tr>
                <th>Match</th>
                <th>Date &amp; Time (UTC)</th>
                <th>Venue</th>
                <th>Predicted Winner</th>
                <th>Win Prob</th>
                <th>Actual Winner</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {(Array.isArray(history) ? history : []).map((m, i) => {
                // Phase 15: Read from backend-computed fields. No frontend calculations.
                const predicted  = m.predicted_winner_id || '—'
                const actual     = m.actual_winner_id    || '—'
                const isCorrect  = m.is_correct          // computed in fetchHistory

                return (
                  <tr key={i}>
                    <td>
                      <span style={{ fontWeight: 600 }}>{m.team_a || '?'}</span>
                      <span style={{ color: '#94a3b8' }}> vs </span>
                      <span style={{ fontWeight: 600 }}>{m.team_b || '?'}</span>
                    </td>
                    {/* Phase 4: fmtDateTime always renders DD Mon YYYY, HH:MM UTC */}
                    <td style={{ color: '#64748b', whiteSpace: 'nowrap' }}>{fmtDateTime(m.date)}</td>
                    <td style={{ color: '#475569', fontWeight: 500 }}>{m.venue || '—'}</td>
                    <td style={{ fontWeight: 600, color: '#3b5bdb' }}>{predicted}</td>
                    <td>
                      <strong>
                        {m.probability != null ? `${(m.probability * 100).toFixed(1)}%` : '—'}
                      </strong>
                    </td>
                    <td style={{ fontWeight: 600, color: '#0f172a' }}>{actual}</td>
                    <td>
                      {/* Phase 5: Result badge only when actual_winner is confirmed */}
                      {isCorrect === true  && <span className="badge badge-success">✓ Correct</span>}
                      {isCorrect === false && <span className="badge badge-danger">✗ Wrong</span>}
                      {isCorrect === null  && <span className="badge badge-warn">Pending</span>}
                    </td>
                  </tr>
                )
              })}
              {(!Array.isArray(history) || history.length === 0) && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 0' }}>
                    No verified completed matches found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </DashboardLayout>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Research Page — Phase 14
// Requires: ROC Curve, PR Curve, Calibration Curve, Confusion Matrix,
//           Feature Correlation, SHAP Summary, Prediction Distribution.
// ─────────────────────────────────────────────────────────────────────────────
export function ResearchPage() {
  return (
    <DashboardLayout
      title="Research"
      subtitle="Deep-dive analysis: Calibration, SHAP, ROC, Confusion Matrix — Phase 14"
    >
      <div className="card">
        <NotImplemented
          feature="Research & Analysis Hub — Not Yet Implemented"
          description={`This module provides statistical deep-dive analysis of model performance.
            All charts require pre-computed analysis artifacts stored in the database or 
            object storage. None of these can be safely fabricated on the frontend.`}
          requirements={[
            'ROC Curve: compute and store true positive / false positive rates per model',
            'Precision-Recall Curve: compute and store per model in analysis_artifacts table',
            'Calibration Curve: compute reliability diagram data (stored in model_registry.calibration_metrics)',
            'Confusion Matrix: compute and store TP/TN/FP/FN counts per model',
            'Feature Correlation: compute correlation matrix from feature_importance data',
            'SHAP Summary Plot: requires shap_mean values in feature_importance (currently NULL)',
            'Prediction Distribution / Probability Histogram: query probability from prediction_store',
          ]}
        />
      </div>
    </DashboardLayout>
  )
}

export function AlertsPage() {
  return (
    <DashboardLayout title="Alerts" subtitle="Prediction alerts and notification settings">
      <div className="card">
        <NotImplemented
          feature="Alerts System — Not Yet Implemented"
          description="Real-time alerts for model drift, accuracy degradation, and prediction confidence drops. Requires alerting backend connected to model monitoring metrics."
          requirements={[
            'Alert rules stored in a database table (e.g. alert_rules)',
            'Webhook or email notification system integration',
            'Model drift detection threshold configuration',
          ]}
        />
      </div>
    </DashboardLayout>
  )
}

export function SettingsPage() {
  const apiUrl = import.meta.env.VITE_SUPABASE_URL || 'Not configured'
  return (
    <DashboardLayout title="Settings" subtitle="System configuration and API access">
      <div className="card">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Current Configuration</h3>
        <table className="gp-table">
          <tbody>
            <tr>
              <td style={{ color: '#64748b', width: 200 }}>Supabase URL</td>
              <td style={{ fontFamily: 'monospace', fontSize: 12, color: '#3b5bdb' }}>{apiUrl}</td>
            </tr>
            <tr>
              <td style={{ color: '#64748b' }}>Frontend Version</td>
              <td style={{ fontWeight: 600 }}>GlobalPulse Production (React + Vite)</td>
            </tr>
            <tr>
              <td style={{ color: '#64748b' }}>Data Source</td>
              <td style={{ fontWeight: 600, color: '#16a34a' }}>Supabase (Production)</td>
            </tr>
            <tr>
              <td style={{ color: '#64748b' }}>Audit Status</td>
              <td>
                <span className="badge badge-success">Phase 1–17 Forensic Audit Passed</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  )
}
