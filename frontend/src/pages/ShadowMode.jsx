import DashboardLayout from '../layouts/DashboardLayout'
import { useShadow, useMetrics } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { fmtDateTime } from '../utils/format'

// ─────────────────────────────────────────────────────────────────────────────
// Shadow Mode Page — VERIFIED past outcomes
// Shows real verified predictions from prediction_store.
// Global accuracy and ROI sourced from dashboard_summary (metrics).
// ─────────────────────────────────────────────────────────────────────────────
export default function ShadowModePage() {
  const { data: predictionsData, isLoading: sl } = useShadow()
  const { data: metrics, isLoading: ml } = useMetrics()

  const predictions = Array.isArray(predictionsData) ? predictionsData : []

  // Global metrics from view
  const accuracy = metrics?.accuracy ?? null
  const roi = metrics?.roi ?? null
  const totalVerified = metrics?.total_predictions ?? 0

  return (
    <DashboardLayout title="Shadow Mode" subtitle="Immutable audit trail of all verified AI predictions vs actual outcomes">
      {/* Summary bar */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        {[
          { label: 'Total Verified Predictions', val: ml ? '—' : totalVerified.toLocaleString(), color: '#3b5bdb' },
          { label: 'Global Accuracy', val: ml || accuracy == null ? '—' : `${(accuracy * 100).toFixed(2)}%`, color: '#7c3aed' },
          { label: 'Global ROI', val: ml || roi == null ? '—' : `${roi > 0 ? '+' : ''}${(roi * 100).toFixed(2)}%`, color: '#059669' },
        ].map(({ label, val, color }) => (
          <div key={label} className="card" style={{ flex: 1 }}>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>{label}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color }}>{val}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Recent Verified Outcomes</h3>
        {sl ? <TableSkeleton rows={10} /> : (
          <table className="gp-table">
            <thead>
              <tr>
                <th>Match</th>
                <th>Venue</th>
                <th>Predicted Winner</th>
                <th>Confidence</th>
                <th>Actual Winner</th>
                <th>Outcome</th>
                <th>Verification Time (UTC)</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((p, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600, fontSize: 12 }}>{p.event_id || '—'}</td>
                  <td style={{ fontSize: 12, color: '#475569' }}>{p.venue || '—'}</td>
                  <td style={{ color: '#3b5bdb', fontWeight: 600 }}>{p.predicted_winner || '—'}</td>
                  <td>{p.confidence != null ? `${(p.confidence * 100).toFixed(1)}%` : '—'}</td>
                  <td style={{ fontWeight: p.actual_winner ? 600 : 400 }}>
                    {p.actual_winner || <span style={{ color: '#94a3b8' }}>Unknown</span>}
                  </td>
                  <td>
                    {p.is_correct === true && <span className="badge badge-success">✓ Correct</span>}
                    {p.is_correct === false && <span className="badge badge-danger">✗ Wrong</span>}
                    {p.is_correct === null && <span className="badge badge-warn">Pending</span>}
                  </td>
                  <td style={{ color: '#94a3b8', fontSize: 12 }}>{fmtDateTime(p.prediction_timestamp)}</td>
                </tr>
              ))}
              {predictions.length === 0 && (
                <tr><td colSpan={7} style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 0' }}>No verified predictions available.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </DashboardLayout>
  )
}
