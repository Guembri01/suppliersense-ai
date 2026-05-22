import { getSeverityBadge, getRiskBgColor } from '../utils'

interface Props {
  label: string
  type?: 'severity' | 'risk' | 'status' | 'criticality'
  className?: string
}

// Criticality = business importance (diamond icon)
// Risk = computed risk level (shield icon)
const CRITICALITY_ICONS: Record<string, string> = {
  critical: '◆',
  high: '◈',
  medium: '◇',
  low: '○',
}

const RISK_ICONS: Record<string, string> = {
  critical: '⚠',
  high: '▲',
  medium: '●',
  low: '✓',
}

function formatLabel(raw: string): string {
  if (!raw) return '—'
  return raw
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function Badge({ label, type = 'severity', className = '' }: Props) {
  let cls = ''
  let prefix = ''

  if (type === 'criticality') {
    // Business importance — diamond icon, rounded-md shape
    cls = getSeverityBadge(label)
    prefix = CRITICALITY_ICONS[label] || '◇'
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium ${cls} ${className}`}
        title={`Business Criticality: ${label}`}
      >
        <span className="text-[10px]">{prefix}</span>
        {formatLabel(label)}
      </span>
    )
  }

  if (type === 'risk') {
    // Risk level — shield/warning icon, rounded-full pill shape
    cls = getRiskBgColor(label)
    prefix = RISK_ICONS[label] || '●'
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cls} ${className}`}
        title={`Risk Level: ${label} (0-25 Low · 25-50 Medium · 50-75 High · 75-100 Critical)`}
      >
        <span className="text-[10px]">{prefix}</span>
        {formatLabel(label)}
      </span>
    )
  }

  if (type === 'severity') {
    cls = getSeverityBadge(label)
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls} ${className}`}>
        {formatLabel(label)}
      </span>
    )
  }

  // status
  cls = 'bg-gray-700 text-gray-300'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls} ${className}`}>
      {formatLabel(label)}
    </span>
  )
}
