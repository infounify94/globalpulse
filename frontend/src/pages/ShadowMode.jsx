import DashboardLayout from '../layouts/DashboardLayout'
import { useShadow } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { fmtDateTime } from '../utils/format'

export default function ShadowModePage() {
  const { data, isLoading } = useShadow()
  const predictions = Array.isArray(data) ? data : []

  const total   = predictions.length
  const correct = predictions.filter(p => p.actual_winner && p.actual_winner === p.predicted_winner).length
  const wrong   = predictions.filter(p => p.actual_winner && p.actual_winner !== p.predicted_winner).length
  const pending = predictions.filter(p => !p.actual_winner).length
  const acc     = total > 0 ? ((correct / (correct + wrong)) * 100).toFixed(1) : '—'

  return (
    <DashboardLayout title="Shadow Mode" subtitle="Immutable audit trail of all AI predictions vs actual outcomes">
      {/* Summary bar */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        {[
          { label: 'Total Predictions', val: total, color: '#3b5bdb' },
          { label: 'Correct',  val: correct, color: '#16a34a' },
          { label: 'Wrong',    val: wrong,   color: '#dc2626' },
          { label: 'Pending',  val: pending, color: '#d97706' },
          { label: 'Accuracy', val: acc !== '—' ? `${acc}%` : '—', color: '#7c3aed' },
        ].map(({ label, val, color }) => (
          <div key={label} className="card" style={{ flex: 1 }}>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>{label}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color }}>{val}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Prediction Log</h3>
        {isLoading ? <TableSkeleton rows={10} /> : (
          <table className="gp-table">
            <thead>
              <tr>
                <th>Match</th><th>Predicted Winner</th><th>Confidence</th><th>Actual Winner</th><th>Outcome</th><th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((p, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600, fontSize: 12 }}>{p.event_id || '—'}</td>
                  <td style={{ color: '#3b5bdb', fontWeight: 600 }}>{p.predicted_winner || '—'}</td>
                  <td>{p.confidence ? `${(p.confidence * 100).toFixed(1)}%` : '—'}</td>
                  <td>{p.actual_winner || <span className="badge badge-warn">Pending</span>}</td>
                  <td>
                    {p.actual_winner ? (
                      <span className={`badge ${p.actual_winner === p.predicted_winner ? 'badge-success' : 'badge-danger'}`}>
                        {p.actual_winner === p.predicted_winner ? '✓ Correct' : '✗ Wrong'}
                      </span>
                    ) : <span className="badge badge-warn">Pending</span>}
                  </td>
                  <td style={{ color: '#94a3b8', fontSize: 12 }}>{fmtDateTime(p.prediction_timestamp)}</td>
                </tr>
              ))}
              {predictions.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>No predictions stored yet.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </DashboardLayout>
  )
}
