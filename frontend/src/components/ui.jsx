// Small presentational primitives shared across pages.
import Icon from './Icon.jsx'
import { TONE } from '../lib/format.js'

/** Colored dot + text label: status is never conveyed by color alone. */
export function StatusLabel({ tone = 'neutral', children, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm ${TONE[tone].ink} ${className}`}>
      <span aria-hidden="true" className={`size-1.5 rounded-full ${TONE[tone].dot}`} />
      {children}
    </span>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`skeleton rounded-xl ${className}`} aria-hidden="true" />
}

export function ErrorState({ title = 'Something went wrong', message, onRetry, children }) {
  return (
    <div role="alert" className="panel p-8 text-center">
      <div className="mx-auto grid size-10 place-items-center rounded-full bg-critical/10 text-critical-ink">
        <Icon name="alert" className="size-5" />
      </div>
      <p className="mt-4 font-medium text-ink">{title}</p>
      {message && <p className="mx-auto mt-1.5 max-w-md text-sm text-ink-2">{message}</p>}
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {onRetry && (
          <button type="button" onClick={onRetry} className="btn-primary !h-10">
            <Icon name="refresh" className="size-4" /> Try again
          </button>
        )}
        {children}
      </div>
    </div>
  )
}

/** Thin meter for a ratio. Fill in the accent hue over a quiet track. */
export function Meter({ value, max = 1, label, valueLabel }) {
  const ratio = Math.max(0, Math.min(1, value / max))
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-3 text-sm">
        <span className="text-ink-2">{label}</span>
        <span className="tabular-nums text-ink">{valueLabel}</span>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-track" role="meter" aria-label={label}
        aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}>
        <div className="h-full rounded-full bg-accent transition-[width] duration-1000 ease-out"
          style={{ width: `${ratio * 100}%` }} />
      </div>
    </div>
  )
}
