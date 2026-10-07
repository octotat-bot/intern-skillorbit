// Small presentational primitives shared across pages.
import Icon from './Icon.jsx'
import { TONE } from '../lib/format.js'

export function Card({ title, subtitle, action, children, className = '', as: Tag = 'section', ...rest }) {
  return (
    <Tag className={`rounded-2xl border border-line bg-card p-5 shadow-sm shadow-black/5 sm:p-6 ${className}`} {...rest}>
      {(title || action) && (
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-base font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-sm text-ink-3">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </Tag>
  )
}

/** Status pill: color + icon + text, never color alone. */
export function StatusBadge({ tone = 'neutral', icon, children, className = '' }) {
  const t = TONE[tone]
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${t.soft} ${t.ink} ${className}`}>
      {icon && <Icon name={icon} className="size-3.5" />}
      {children}
    </span>
  )
}

export function Chip({ children, variant = 'neutral', title }) {
  const styles = {
    matched: 'border-good/40 bg-good/10 text-good-ink',
    missing: 'border-critical/40 bg-critical/10 text-critical-ink',
    neutral: 'border-line bg-card-2 text-ink-2',
  }
  const icon = { matched: 'check', missing: 'x' }[variant]
  return (
    <li title={title} className={`inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-xs font-medium ${styles[variant]}`}>
      {icon && <Icon name={icon} className="size-3" />}
      {children}
    </li>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`skeleton rounded-lg ${className}`} aria-hidden="true" />
}

export function ErrorState({ title = 'Something went wrong', message, onRetry, children }) {
  return (
    <div role="alert" className="rounded-2xl border border-critical/40 bg-critical/10 p-5">
      <div className="flex items-start gap-3">
        <Icon name="alert" className="mt-0.5 size-5 shrink-0 text-critical-ink" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-ink">{title}</p>
          {message && <p className="mt-1 text-sm text-ink-2">{message}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            {onRetry && (
              <button type="button" onClick={onRetry} className="btn-secondary">
                <Icon name="refresh" className="size-4" /> Try again
              </button>
            )}
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

/** Horizontal meter for a ratio; the track is a lighter step of the fill hue. */
export function Meter({ value, max = 1, tone = 'neutral', label, valueLabel }) {
  const ratio = Math.max(0, Math.min(1, value / max))
  const fill = TONE[tone].fill
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
        <span className="text-ink-2">{label}</span>
        <span className="font-medium text-ink tabular-nums">{valueLabel}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full" style={{ background: `color-mix(in srgb, ${fill} 22%, transparent)` }}
        role="meter" aria-valuemin={0} aria-valuemax={max} aria-valuenow={value} aria-label={label}>
        <div className="h-full rounded-full transition-[width] duration-700 ease-out" style={{ width: `${ratio * 100}%`, background: fill }} />
      </div>
    </div>
  )
}
