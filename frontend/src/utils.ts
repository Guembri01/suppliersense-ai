export function getRiskBand(score: number): string {
  if (score < 25) return 'low'
  if (score < 50) return 'medium'
  if (score < 75) return 'high'
  return 'critical'
}

export function getRiskColor(band: string): string {
  switch (band) {
    case 'low': return 'text-green-400'
    case 'medium': return 'text-yellow-400'
    case 'high': return 'text-orange-400'
    case 'critical': return 'text-red-400'
    default: return 'text-gray-400'
  }
}

export function getRiskBgColor(band: string): string {
  switch (band) {
    case 'low': return 'bg-green-900/40 text-green-300'
    case 'medium': return 'bg-yellow-900/40 text-yellow-300'
    case 'high': return 'bg-orange-900/40 text-orange-300'
    case 'critical': return 'bg-red-900/40 text-red-300'
    default: return 'bg-gray-800 text-gray-400'
  }
}

export function getSeverityBadge(severity: string): string {
  switch (severity) {
    case 'low': return 'bg-green-800 text-green-200'
    case 'medium': return 'bg-yellow-800 text-yellow-200'
    case 'high': return 'bg-orange-800 text-orange-200'
    case 'critical': return 'bg-red-800 text-red-200'
    // cert statuses
    case 'valid': return 'bg-green-800 text-green-200'
    case 'expiring': return 'bg-yellow-800 text-yellow-200'
    case 'expired': return 'bg-red-800 text-red-200'
    default: return 'bg-gray-700 text-gray-300'
  }
}

export function fmtDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

export function fmtNum(n: number | null | undefined, decimals = 0): string {
  if (n === null || n === undefined) return '—'
  return n.toLocaleString('en-US', { maximumFractionDigits: decimals })
}

export function fmtCurrency(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

/** Convert snake_case / enum values to Title Case display labels */
export function formatLabel(raw: string | null | undefined): string {
  if (!raw) return '—'
  return raw
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}
