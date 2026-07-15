import { Bell, Search, ChevronDown } from 'lucide-react'
import { useStatus } from '../hooks/useApi'

export default function Navbar({ title, subtitle }) {
  const { data: status } = useStatus()
  const isOnline = !!status

  return (
    <header style={{
      position: 'fixed', top: 0, right: 0, left: 220, zIndex: 99,
      background: 'rgba(9, 9, 11, 0.5)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
      borderBottom: '1px solid var(--color-border)', padding: '0 28px',
      height: 60, display: 'flex', alignItems: 'center', justifyContent: 'space-between'
    }}>
      <div>
        <h1 style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text)', letterSpacing: '0.02em' }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 12, color: 'var(--color-muted)', marginTop: 1 }}>{subtitle}</p>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {/* Backend Status */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'var(--color-surface)', border: '1px solid var(--color-border)',
          borderRadius: 8, padding: '6px 12px', fontSize: 12, color: 'var(--color-muted)'
        }}>
          <span className={`status-dot ${isOnline ? 'status-online' : 'status-offline'}`} />
          <span style={{ fontWeight: 500, color: isOnline ? '#16a34a' : '#dc2626' }}>
            {isOnline ? 'Backend Online' : 'Connecting…'}
          </span>
        </div>

        {/* Notification Bell */}
        <button style={{
          width: 36, height: 36, borderRadius: 8, border: '1px solid var(--color-border)',
          background: 'var(--color-surface)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', cursor: 'pointer', position: 'relative',
          transition: 'all 0.2s ease'
        }} className="hover:border-primary">
          <Bell size={15} color="var(--color-muted)" />
        </button>

        {/* Avatar */}
        <div style={{
          width: 34, height: 34, borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--color-primary), #7c3aed)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'white', fontSize: 13, fontWeight: 700, cursor: 'pointer',
          boxShadow: '0 4px 10px rgba(59, 130, 246, 0.4)'
        }}>GP</div>
      </div>
    </header>
  )
}
