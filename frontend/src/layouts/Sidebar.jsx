import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Zap, Eye, Cpu, FlaskConical,
  BarChart3, Network, History, BookOpen, Settings, Bell
} from 'lucide-react'
import { useStatus } from '../hooks/useApi'

const NAV = [
  { to: '/',                 icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/predictions',      icon: Zap,             label: 'Predictions' },
  { to: '/shadow',           icon: Eye,             label: 'Shadow Mode' },
  { to: '/models',           icon: Cpu,             label: 'Models' },
  { to: '/experiments',      icon: FlaskConical,    label: 'Experiments' },
  { to: '/features',         icon: BarChart3,       label: 'Feature Importance' },
  { to: '/patterns',         icon: Network,         label: 'Pattern Memory' },
  { to: '/history',          icon: History,         label: 'Historical Replay' },
  { to: '/research',         icon: BookOpen,        label: 'Research' },
  { to: '/alerts',           icon: Bell,            label: 'Alerts' },
  { to: '/settings',         icon: Settings,        label: 'Settings' },
]

export default function Sidebar() {
  const { data: status } = useStatus()
  const isOnline = !!status

  return (
    <aside style={{
      width: 220, minHeight: '100vh', background: '#fff',
      borderRight: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column',
      padding: '0 12px', position: 'fixed', top: 0, left: 0, bottom: 0, zIndex: 100,
      overflow: 'hidden'
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 8px 16px', borderBottom: '1px solid #f1f5f9' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, #3b5bdb, #7c3aed)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'white', fontWeight: 800, fontSize: 15
          }}>GP</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: '#0f172a' }}>GlobalPulse</div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>Prediction Intelligence</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, paddingTop: 12, overflowY: 'auto' }}>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            style={{ marginBottom: 2 }}
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: '12px 8px', borderTop: '1px solid #f1f5f9' }}>
        <div style={{ background: '#f8fafc', borderRadius: 10, padding: '10px 12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: 'linear-gradient(135deg, #3b5bdb, #7c3aed)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'white', fontSize: 11, fontWeight: 700
            }}>GP</div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#0f172a' }}>GlobalPulse AI</div>
              <div style={{ fontSize: 10, color: '#94a3b8' }}>Champion Model</div>
            </div>
          </div>
          <div style={{ fontSize: 11, color: '#64748b', display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div>Model: <span style={{ color: '#0f172a', fontWeight: 500 }}>{status?.champion_model_version || '—'}</span></div>
            <div>Dataset: <span style={{ color: '#0f172a', fontWeight: 500 }}>{status?.dataset_version || '—'}</span></div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 }}>
            <span className={`status-dot ${isOnline ? 'status-online' : 'status-offline'}`} />
            <span style={{ fontSize: 11, color: isOnline ? '#16a34a' : '#dc2626', fontWeight: 500 }}>
              {isOnline ? 'All Systems Operational' : 'Connecting…'}
            </span>
          </div>
        </div>
      </div>
    </aside>
  )
}
