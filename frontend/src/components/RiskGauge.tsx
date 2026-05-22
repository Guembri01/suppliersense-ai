import { getRiskBand, getRiskColor } from '../utils'

interface Props {
  score: number
  size?: 'sm' | 'md' | 'lg'
}

export default function RiskGauge({ score, size = 'md' }: Props) {
  const band = getRiskBand(score)
  const color = getRiskColor(band)
  const sizeClasses = size === 'sm' ? 'w-12 h-12 text-xs' : size === 'lg' ? 'w-24 h-24 text-xl' : 'w-16 h-16 text-sm'

  const radius = size === 'sm' ? 18 : size === 'lg' ? 38 : 26
  const cx = size === 'sm' ? 24 : size === 'lg' ? 48 : 32
  const cy = cx
  const strokeWidth = size === 'sm' ? 4 : size === 'lg' ? 6 : 5
  const circumference = 2 * Math.PI * radius
  const dash = (score / 100) * circumference

  const strokeColor = band === 'low' ? '#4ade80' : band === 'medium' ? '#facc15' : band === 'high' ? '#fb923c' : '#f87171'

  return (
    <div className={`relative ${sizeClasses} flex items-center justify-center`}>
      <svg className="absolute inset-0 -rotate-90" width={cx * 2} height={cy * 2}>
        <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#374151" strokeWidth={strokeWidth} />
        <circle
          cx={cx} cy={cy} r={radius} fill="none"
          stroke={strokeColor} strokeWidth={strokeWidth}
          strokeDasharray={`${dash} ${circumference - dash}`}
          strokeLinecap="round"
        />
      </svg>
      <div className={`relative font-bold ${color}`}>
        {score.toFixed(0)}
      </div>
    </div>
  )
}
