import { Bell, Search, ChevronDown } from 'lucide-react'
import { useStatus } from '../hooks/useApi'

export default function Navbar({ title, subtitle }) {
  const { data: status } = useStatus()
  const isOnline = !!status

  return (
    <header style={{
      position: 'fixed', top: 0, right: 0, left: 220, zIndex: 99,
      background: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(12px)',
      borderBottom: '1px solid #e2e8f0', padding: '0 28px',
      height: 60, display: 'flex', alignItems: 'center', justifyContent: 'space-between'
    }}>
      <div>
        <h1 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 1 }}>{subtitle}</p>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {/* Backend Status */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: '#f8fafc', border: '1px solid #e2e8f0',
          borderRadius: 8, padding: '6px 12px', fontSize: 12, color: '#64748b'
        }}>
          <span className={`status-dot ${isOnline ? 'status-online' : 'status-offline'}`} />
          <span style={{ fontWeight: 500, color: isOnline ? '#16a34a' : '#dc2626' }}>
            {isOnline ? 'Backend Online' : 'Connecting…'}
          </span>
        </div>

        {/* Notification Bell */}
        <button style={{
          width: 36, height: 36, borderRadius: 8, border: '1px solid #e2e8f0',
          background: '#fff', display: 'flex', alignItems: 'center',
          justifyContent: 'center', cursor: 'pointer', position: 'relative'
        }}>
          <Bell size={15} color="#64748b" />
        </button>

        {/* Avatar */}
        <div style={{
          width: 34, height: 34, borderRadius: '50%',
          background: 'linear-gradient(135deg, #3b5bdb, #7c3aed)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'white', fontSize: 13, fontWeight: 700, cursor: 'pointer'
        }}>GP</div>
      </div>
    </header>
  )
}
