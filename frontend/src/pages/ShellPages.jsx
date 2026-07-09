import DashboardLayout from '../layouts/DashboardLayout'

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
  return (
    <DashboardLayout title="Historical Replay" subtitle="Walk-forward analysis and out-of-sample validation">
      <div className="card"><ComingSoon feature="Historical Replay Engine" /></div>
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
