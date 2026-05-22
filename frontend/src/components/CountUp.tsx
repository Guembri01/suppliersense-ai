import { useEffect, useRef, useState } from 'react'

interface Props {
  to: number
  durationMs?: number
  decimals?: number
  className?: string
}

export default function CountUp({ to, durationMs = 900, decimals = 0, className = '' }: Props) {
  const [val, setVal] = useState(0)
  const fromRef = useRef(0)

  useEffect(() => {
    const start = performance.now()
    const from = fromRef.current
    const diff = to - from
    let raf = 0
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / durationMs)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - p, 3)
      setVal(from + diff * eased)
      if (p < 1) raf = requestAnimationFrame(tick)
      else fromRef.current = to
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [to, durationMs])

  return (
    <span className={className} style={{ fontVariantNumeric: 'tabular-nums' }}>
      {val.toLocaleString('en-US', { maximumFractionDigits: decimals })}
    </span>
  )
}
