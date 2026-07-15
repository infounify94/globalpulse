import { CardSkeleton } from './Skeleton'

export function MetricCard({ label, value, sub, icon: Icon, color = '#3b5bdb', loading }) {
  if (loading) return <CardSkeleton />
  return (
    <div className="glass-card" style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <span style={{ fontSize: 13, color: 'var(--color-muted)', fontWeight: 500, letterSpacing: '0.02em' }}>{label}</span>
        {Icon && (
          <div style={{
            width: 34, height: 34, borderRadius: 10, display: 'flex', alignItems: 'center',
            justifyContent: 'center', background: `${color}25`, border: `1px solid ${color}40`,
            boxShadow: `0 0 15px ${color}30`
          }}>
            <Icon size={16} color={color} />
          </div>
        )}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--color-text)', marginBottom: 4, textShadow: '0 2px 10px rgba(255,255,255,0.1)' }}>
        {value ?? '—'}
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--color-muted)' }}>{sub}</div>}
    </div>
  )
}
