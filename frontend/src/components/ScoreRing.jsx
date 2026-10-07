// Thin ring meter around the hero score. The arc carries status color;
// the status label below states it in words.
import { useCountUp } from '../hooks/useCountUp.js'
import { TONE, scoreStatus } from '../lib/format.js'
import { StatusLabel } from './ui.jsx'

export default function ScoreRing({ value, label, band, size = 188, stroke = 5 }) {
  const status = scoreStatus(value)
  const shown = useCountUp(value)
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius

  return (
    <figure className="flex flex-col items-center" aria-label={`${label}: ${value} out of 100, ${band || status.label}`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} style={{ stroke: 'var(--track)' }} />
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={circumference * (1 - shown / 100)}
            style={{ stroke: TONE[status.tone].fill }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[64px] font-light leading-none tracking-[-0.04em] text-ink">{shown}</span>
          <span className="mt-2 text-xs text-ink-3">out of 100</span>
        </div>
      </div>
      <figcaption className="mt-5">
        <StatusLabel tone={status.tone}>{band || status.label}</StatusLabel>
      </figcaption>
    </figure>
  )
}
