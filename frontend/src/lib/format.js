// Shared display helpers: score bands, priority styling, labels.

/** Status for a 0-100 score. Status colors always ship with an icon and a label. */
export function scoreStatus(value) {
  if (value >= 70) return { tone: 'good', label: value >= 85 ? 'Excellent' : 'Good', icon: 'check' }
  if (value >= 50) return { tone: 'warning', label: 'Fair', icon: 'alert' }
  return { tone: 'critical', label: 'Needs work', icon: 'alert' }
}

export const TONE = {
  good: { fill: 'var(--good)', ink: 'text-good-ink', soft: 'bg-good/15' },
  warning: { fill: 'var(--warning)', ink: 'text-warning-ink', soft: 'bg-warning/15' },
  critical: { fill: 'var(--critical)', ink: 'text-critical-ink', soft: 'bg-critical/15' },
  neutral: { fill: 'var(--accent)', ink: 'text-accent-ink', soft: 'bg-accent/15' },
}

export const PRIORITY = {
  high: { tone: 'critical', label: 'High priority', icon: 'alert' },
  medium: { tone: 'warning', label: 'Medium priority', icon: 'info' },
  low: { tone: 'neutral', label: 'Low priority', icon: 'info' },
}

export function impactLabel({ points, target }) {
  if (!points) return target === 'readability' ? 'Readability' : null
  const unit = target === 'ats' ? 'ATS pts' : 'pts'
  return `+${points} ${unit}`
}

export const pct = (value) => `${Math.round(value * 100)}%`
