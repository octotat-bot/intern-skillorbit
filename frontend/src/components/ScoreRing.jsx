// Ring meter + hero figure for a 0-100 score. Fill color carries status;
// the status label and icon beside it make the meaning explicit.
import { useEffect, useState } from 'react'
import Icon from './Icon.jsx'
import { TONE, scoreStatus } from '../lib/format.js'

export default function ScoreRing({ value, label, size = 168, stroke = 12, hero = false, statusText }) {
  const status = scoreStatus(value)
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  // Animate from 0 unless the user prefers reduced motion (then render the final value directly).
  const reduce = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const [shown, setShown] = useState(reduce ? value : 0)
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(value))
    return () => cancelAnimationFrame(id)
  }, [value])
  const fill = TONE[status.tone].fill

  return (
    <figure className="flex flex-col items-center gap-3" aria-label={`${label}: ${value} out of 100, ${status.label}`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke}
            style={{ stroke: `color-mix(in srgb, ${fill} 20%, transparent)` }} />
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={circumference * (1 - shown / 100)}
            style={{ stroke: fill, transition: 'stroke-dashoffset 900ms cubic-bezier(.2,.7,.2,1)' }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${hero ? 'text-5xl' : 'text-3xl'} font-semibold leading-none text-ink`}>{value}</span>
          <span className="mt-1 text-xs text-ink-3">out of 100</span>
        </div>
      </div>
      <figcaption className="flex flex-col items-center gap-1 text-center">
        <span className="text-sm font-medium text-ink-2">{label}</span>
        <span className={`inline-flex items-center gap-1 text-sm font-semibold ${TONE[status.tone].ink}`}>
          <Icon name={status.icon} className="size-4" />
          {statusText || status.label}
        </span>
      </figcaption>
    </figure>
  )
}
