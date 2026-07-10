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
  const d = new Date(str)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

/**
 * Always renders: "19 Dec 2026, 05:30 UTC"
 * Phase 4 mandate: NEVER display partial dates like "19 Dec" without year.
 */
export function fmtDateTime(str) {
  if (!str) return '—'
  const d = new Date(str)
  if (isNaN(d.getTime())) return '—'
  const day = String(d.getUTCDate()).padStart(2, '0')
  const month = d.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })
  const year = d.getUTCFullYear()
  const hh = String(d.getUTCHours()).padStart(2, '0')
  const mm = String(d.getUTCMinutes()).padStart(2, '0')
  return `${day} ${month} ${year}, ${hh}:${mm} UTC`
}

export function getConfidenceBadge(conf) {
  const pct = (conf || 0) * 100
  if (pct >= 80) return 'badge-success'
  if (pct >= 60) return 'badge-info'
  if (pct >= 40) return 'badge-warn'
  return 'badge-danger'
}
