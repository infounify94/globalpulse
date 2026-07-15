import DashboardLayout from '../layouts/DashboardLayout'
import { useMatches } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { WakeupBanner } from '../components/ui/Banners'
import { fmtDateTime } from '../utils/format'
import { AlertTriangle } from 'lucide-react'

// ─────────────────────────────────────────────────────────────────────────────
// Predictions Page — shows Upcoming matches (PENDING with future date)
// Phase 15: No fabricated data. Real probabilities, real signals from DB.
// ─────────────────────────────────────────────────────────────────────────────
export default function PredictionsPage() {
  const { data: matches, isLoading, isError } = useMatches()

  return (
    <DashboardLayout title="Upcoming Predictions" subtitle="Matches scheduled in the future with active predictions">
      {isError && <WakeupBanner />}
      <div className="glass-card">
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600 }}>Active Predictions</h3>
          <p style={{ fontSize: 12, color: 'var(--color-muted)', marginTop: 2 }}>Sourced from the Champion Model</p>
        </div>
        {isLoading ? <TableSkeleton rows={10} /> : (
          <table className="gp-table">
            <thead>
              <tr>
                <th>Match</th>
                <th>Date & Time (UTC)</th>
                <th>Venue</th>
                <th>Match Type</th>
                <th>Predicted Winner</th>
                <th>Win Prob</th>
                <th>Confidence</th>
                <th>Prediction Model</th>
                <th>Top Features</th>
              </tr>
            </thead>
            <tbody>
              {(Array.isArray(matches) ? matches : []).map((m, i) => {
                const prob = m.team_a_probability ?? null
                const winner = m.predicted_winner || '—'
                const winProb = m.probability ?? null
                const venueStr = m.venue || '—'
                const topFactors = m.top_driving_features || []
                const confPct = m.confidence != null ? `${(m.confidence * 100).toFixed(1)}%` : '—'

                return (
                  <tr key={i}>
                    <td>
                      <span style={{ fontWeight: 600 }}>{m.team_a || '?'}</span> <span style={{ color: 'var(--color-muted)' }}>vs</span> <span style={{ fontWeight: 600 }}>{m.team_b || '?'}</span>
                    </td>
                    <td style={{ color: 'var(--color-muted)', whiteSpace: 'nowrap' }}>{fmtDateTime(m.date)}</td>
                    <td style={{ color: '#475569', fontWeight: 500 }}>{venueStr}</td>
                    <td style={{ fontSize: 11, color: 'var(--color-muted)' }}>{m.match_type || '—'}</td>
                    <td style={{ fontWeight: 600, color: '#3b5bdb' }}>{winner}</td>
                    <td><strong>{winProb != null ? `${(winProb * 100).toFixed(1)}%` : '—'}</strong></td>
                    <td>
                      {m.confidence != null ? (
                        <span className={`badge ${m.confidence > 0.65 ? 'badge-success' : 'badge-warn'}`}>
                          {confPct}
                        </span>
                      ) : '—'}
                    </td>
                    <td style={{ fontSize: 10, color: 'var(--color-muted)', fontFamily: 'monospace', maxWidth: 120, wordBreak: 'break-all' }}>
                      {m.model_version ? m.model_version.slice(0, 20) + '…' : <span style={{ color: 'var(--color-muted)' }}>Champion</span>}
                    </td>
                    <td style={{ color: 'var(--color-muted)', fontSize: 11, maxWidth: 200, whiteSpace: 'normal' }}>
                      {topFactors.length > 0
                        ? topFactors.map(f => `${f.name} (${f.impact})`).join(', ')
                        : '—'}
                    </td>
                  </tr>
                )
              })}
              {(!Array.isArray(matches) || matches.length === 0) && (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', color: 'var(--color-muted)', padding: '40px 0' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                      <AlertTriangle size={24} color="#d97706" />
                      <div>No upcoming matches found in the prediction store.</div>
                      <div style={{ fontSize: 11 }}>Only matches with future dates and PENDING status appear here.</div>
                    </div>
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
