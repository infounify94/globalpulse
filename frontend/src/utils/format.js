export function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

export function fmt(val, decimals = 1) {
  if (val == null) return '—'
  return Number(val).toFixed(decimals)
}

export function fmtPct(val) {
  if (val == null) return '—'
  return `${(val * 100).toFixed(1)}%`
}

export function fmtDate(str) {
  if (!str) return '—'
  return new Date(str).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function fmtDateTime(str) {
  if (!str) return '—'
  return new Date(str).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function getConfidenceBadge(conf) {
  const pct = (conf || 0) * 100
  if (pct >= 80) return 'badge-success'
  if (pct >= 60) return 'badge-info'
  if (pct >= 40) return 'badge-warn'
  return 'badge-danger'
}
