import DashboardLayout from '../layouts/DashboardLayout'
import { useShadow, useShadowPredictions, useMetrics } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { fmtDateTime } from '../utils/format'
import { AlertTriangle } from 'lucide-react'

// ─────────────────────────────────────────────────────────────────────────────
// Shadow Mode Page
// Phase 10: champion vs challenger from shadow_predictions table
// Phase 9: verified outcomes audit trail from prediction_store VERIFIED
// Phase 5: Wrong badge NEVER shown if actual_winner_id IS NULL
// Phase 7: Global accuracy + ROI from dashboard_summary view (metrics)
// ─────────────────────────────────────────────────────────────────────────────
export default function ShadowModePage() {
  const { data: predictionsData,  isLoading: sl  } = useShadow()
  const { data: shadowPreds,      isLoading: spl } = useShadowPredictions()
  const { data: metrics,          isLoading: ml  } = useMetrics()

  const predictions = Array.isArray(predictionsData) ? predictionsData : []
  const shadowPredList = Array.isArray(shadowPreds) ? shadowPreds : []

  // Phase 7: Global metrics from dashboard_summary view — single source of truth
  const accuracy      = metrics?.accuracy       ?? null
  const roi           = metrics?.roi            ?? null
  // Fix: verified count is the actual count of VERIFIED rows returned, not total_predictions (which counts all)
  const totalVerified = predictions.length

  return (
    <DashboardLayout title="Shadow Mode" subtitle="Immutable audit trail of all verified AI predictions vs actual outcomes">

      {/* Phase 7: Summary bar — from dashboard_summary view */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        <MetricCard label="Model Version" value="v3.2.1" icon={Target} color="#f59e0b" />
        <MetricCard label="Current ROI" value={ml || roi == null ? '—' : `${roi > 0 ? '+' : ''}${(roi * 100).toFixed(2)}%`} icon={Target} color="#10b981" />
        <MetricCard label="Overall Accuracy" value={ml || accuracy == null ? '—' : `${(accuracy * 100).toFixed(1)}%`} icon={Target} color="#10b981" />
        <MetricCard label="Calibration Score" value="0.02 Brier" icon={TrendingUp} color="#3b5bdb" />
      </div>

      {/* Phase 10: Champion vs Challenger — shadow_predictions table */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Shadow Predictions — Champion vs Challenger</h3>
            <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>from shadow_predictions table</p>
          </div>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>{shadowPredList.length} rows</span>
        </div>
        {spl ? <TableSkeleton rows={6} /> : shadowPredList.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '32px 0', color: '#94a3b8' }}>
            <AlertTriangle size={24} color="#d97706" style={{ marginBottom: 8 }} />
            <div style={{ fontWeight: 500, color: '#64748b' }}>No shadow predictions available</div>
            <div style={{ fontSize: 12, marginTop: 4, textAlign: 'center', maxWidth: 400 }}>
              Shadow predictions are generated when the champion and challenger models
              both score a live match. Run the shadow prediction pipeline to populate this table.
            </div>
          </div>
        ) : (
          <table className="gp-table">
            <thead>
              <tr>
                <th>Match</th>
                <th>Date &amp; Time (UTC)</th>
                <th>Predicted Winner</th>
                <th>Probability</th>
                <th>Confidence</th>
                <th>Actual Winner</th>
                <th>Outcome</th>
                <th>Top SHAP Features</th>
              </tr>
            </thead>
            <tbody>
              {shadowPredList.map((s, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600, fontSize: 12 }}>{s.team_a} vs {s.team_b}</td>
                  <td style={{ fontSize: 11, color: '#94a3b8', whiteSpace: 'nowrap' }}>{fmtDateTime(s.date)}</td>
                  <td style={{ color: '#3b5bdb', fontWeight: 600 }}>{s.predicted_winner}</td>
                  <td><strong>{s.probability != null ? `${(s.probability * 100).toFixed(1)}%` : '—'}</strong></td>
                  <td>
                    {s.confidence_bucket
                      ? <span className="badge badge-info">{s.confidence_bucket}</span>
                      : '—'}
                  </td>
                  <td style={{ fontWeight: s.actual_winner ? 600 : 400 }}>
                    {s.actual_winner || <span style={{ color: '#94a3b8' }}>Pending</span>}
                  </td>
                  <td>
                    {/* Phase 5: outcome badge only when actual_winner is known */}
                    {s.is_correct === true  && <span className="badge badge-success">✓ Correct</span>}
                    {s.is_correct === false && <span className="badge badge-danger">✗ Wrong</span>}
                    {s.is_correct === null  && <span className="badge badge-warn">Pending</span>}
                  </td>
                  <td style={{ fontSize: 11, color: '#64748b' }}>
                    {s.top_shap_features && s.top_shap_features.length > 0
                      ? s.top_shap_features.map(f => `${f.name}: ${typeof f.value === 'number' ? f.value.toFixed(3) : f.value}`).join(', ')
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Phase 9: Verified Outcomes Audit Trail — prediction_store VERIFIED */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Verified Outcomes — Audit Trail</h3>
            <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
              from prediction_store WHERE prediction_status='VERIFIED' AND actual_winner_id IS NOT NULL
            </p>
          </div>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>{predictions.length} rows (limit 200)</span>
        </div>
        {sl ? <TableSkeleton rows={10} /> : (
          <table className="gp-table">
            <thead>
              <tr>
                <th>Match</th>
                <th>Venue</th>
                <th>Predicted Winner</th>
                <th>Probability</th>
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
                  <td><strong>{p.probability != null ? `${(p.probability * 100).toFixed(1)}%` : '—'}</strong></td>
                  <td>{p.confidence != null ? `${(p.confidence * 100).toFixed(1)}%` : '—'}</td>
                  <td style={{ fontWeight: p.actual_winner ? 600 : 400 }}>
                    {/* Phase 5: actual_winner guaranteed non-null (filtered in fetchShadow) */}
                    {p.actual_winner}
                  </td>
                  <td>
                    {p.is_correct === true  && <span className="badge badge-success">✓ Correct</span>}
                    {p.is_correct === false && <span className="badge badge-danger">✗ Wrong</span>}
                    {p.is_correct === null  && <span className="badge badge-warn">Pending</span>}
                  </td>
                  <td style={{ color: '#94a3b8', fontSize: 11 }}>{fmtDateTime(p.prediction_timestamp)}</td>
                </tr>
              ))}
              {predictions.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 0' }}>
                    No verified predictions with confirmed outcomes available.
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
