interface Props {
  size?: number
  withWordmark?: boolean
  className?: string
}

export default function Logo({ size = 36, withWordmark = false, className = '' }: Props) {
  const id = `lg-${size}`
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg width={size} height={size} viewBox="0 0 36 36" fill="none" aria-hidden="true">
        <defs>
          <linearGradient id={`${id}-bg`} x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#a855f7" />
          </linearGradient>
          <linearGradient id={`${id}-fg`} x1="6" y1="6" x2="30" y2="30" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#f8fafc" />
            <stop offset="100%" stopColor="#c4b5fd" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="36" height="36" rx="10" fill={`url(#${id}-bg)`} />
        <path
          d="M9 18 L15 24 L27 12"
          stroke={`url(#${id}-fg)`}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <circle cx="27" cy="12" r="2.2" fill="#fbbf24" opacity="0.95" />
      </svg>
      {withWordmark && (
        <span className="flex flex-col leading-tight">
          <span className="font-bold text-white text-sm tracking-tight">SupplierSense</span>
          <span className="text-[10px] text-indigo-300/80 tracking-wide uppercase">AI</span>
        </span>
      )}
    </span>
  )
}
