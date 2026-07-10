import DashboardLayout from '../layouts/DashboardLayout'
import { useHistory } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { fmtDateTime } from '../utils/format'

function ComingSoon({ feature }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 300, color: '#94a3b8' }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>🔮</div>
      <h3 style={{ fontSize: 18, color: '#64748b', marginBottom: 8 }}>{feature}</h3>
      <p style={{ fontSize: 13, maxWidth: 400, textAlign: 'center' }}>
        This module is under construction and will be connected once the corresponding backend endpoints are available.
      </p>
    </div>
  )
}

export function PatternMemoryPage() {
  return (
    <DashboardLayout title="Pattern Memory" subtitle="Nearest historical match patterns and embedding similarity">
      <div className="card"><ComingSoon feature="Pattern Memory Engine" /></div>
    </DashboardLayout>
  )
}

export function HistoricalReplayPage() {
  const { data: history, isLoading, isError } = useHistory()

  return (
    <DashboardLayout title="Historical Replay" subtitle="Completed and verified match predictions">
      <div className="card">
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600 }}>Completed Matches Audit Trail</h3>
          <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>Verified outcomes compared directly against XGBoost AI probabilities</p>
        </div>
        {isLoading ? <TableSkeleton rows={10} /> : (
          <table className="gp-table">
            <thead>
              <tr>
                <th>Match</th><th>Date & Time</th><th>Venue</th><th>Predicted Winner</th><th>Win Prob</th><th>Actual Winner</th><th>Result</th>
              </tr>
            </thead>
            <tbody>
              {(Array.isArray(history) ? history : []).map((m, i) => {
                const prob = m.team_a_probability ?? 0.5
                const predicted = prob > 0.5 ? m.team_a : m.team_b
                const winProb = prob > 0.5 ? prob : 1 - prob
                const isCorrect = (m.actual_winner_id === predicted) || (m.is_correct === true)
                return (
                  <tr key={i}>
                    <td><span style={{ fontWeight: 600 }}>{m.team_a}</span> <span style={{ color: '#94a3b8' }}>vs</span> <span style={{ fontWeight: 600 }}>{m.team_b}</span></td>
                    <td style={{ color: '#64748b', whiteSpace: 'nowrap' }}>{fmtDateTime(m.date)}</td>
                    <td style={{ color: '#475569', fontWeight: 500 }}>{m.venue || m.match_type || 'Unknown Venue'}</td>
                    <td style={{ fontWeight: 600, color: '#3b5bdb' }}>{predicted}</td>
                    <td><strong>{(winProb * 100).toFixed(1)}%</strong></td>
                    <td style={{ fontWeight: 600, color: '#0f172a' }}>{m.actual_winner_id || '—'}</td>
                    <td>
                      <span className={`badge ${isCorrect ? 'badge-success' : 'badge-warn'}`}>
                        {isCorrect ? 'Correct ✅' : 'Incorrect ❌'}
                      </span>
                    </td>
                  </tr>
                )
              })}
              {(!Array.isArray(history) || history.length === 0) && (
                <tr><td colSpan={7} style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>No verified completed matches yet.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </DashboardLayout>
  )
}

export function ResearchPage() {
  return (
    <DashboardLayout title="Research" subtitle="Deep-dive analysis: Calibration, SHAP, ROC, Confusion Matrix">
      <div className="card"><ComingSoon feature="Research & Analysis Hub" /></div>
    </DashboardLayout>
  )
}

export function AlertsPage() {
  return (
    <DashboardLayout title="Alerts" subtitle="Prediction alerts and notification settings">
      <div className="card"><ComingSoon feature="Alerts System" /></div>
    </DashboardLayout>
  )
}

export function SettingsPage() {
  const apiUrl = import.meta.env.VITE_API_URL || 'Not configured'
  return (
    <DashboardLayout title="Settings" subtitle="System configuration and API access">
      <div className="card">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Current Configuration</h3>
        <table className="gp-table">
          <tbody>
            <tr>
              <td style={{ color: '#64748b' }}>Backend API URL</td>
              <td style={{ fontFamily: 'monospace', fontSize: 12, color: '#3b5bdb' }}>{apiUrl}</td>
            </tr>
            <tr>
              <td style={{ color: '#64748b' }}>Frontend Version</td>
              <td style={{ fontWeight: 600 }}>GlobalPulse v4.0 (React + Vite)</td>
            </tr>
            <tr>
              <td style={{ color: '#64748b' }}>Prediction Domain</td>
              <td style={{ fontWeight: 600 }}>Cricket (domain-agnostic architecture)</td>
            </tr>
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  )
}
