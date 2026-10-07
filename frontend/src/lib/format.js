// Shared display helpers: score bands, priority styling, labels.

/** Status for a 0-100 score. Status color is always shown next to its label. */
export function scoreStatus(value) {
  if (value >= 85) return { tone: 'good', label: 'Excellent' }
  if (value >= 70) return { tone: 'good', label: 'Good' }
  if (value >= 50) return { tone: 'warning', label: 'Fair' }
  return { tone: 'critical', label: 'Needs work' }
}

export const TONE = {
  good: { fill: 'var(--good)', dot: 'bg-good', ink: 'text-good-ink' },
  warning: { fill: 'var(--warning)', dot: 'bg-warning', ink: 'text-warning-ink' },
  critical: { fill: 'var(--critical)', dot: 'bg-critical', ink: 'text-critical-ink' },
  neutral: { fill: 'var(--ink-3)', dot: 'bg-ink-3', ink: 'text-ink-2' },
}

export const PRIORITY = {
  high: { tone: 'critical', label: 'High' },
  medium: { tone: 'warning', label: 'Medium' },
  low: { tone: 'neutral', label: 'Low' },
}

/** "+4" with its unit, or null when a suggestion has no point impact. */
export function impactParts({ points, target }) {
  if (!points) return null
  return { value: `+${points}`, unit: target === 'ats' ? 'ATS' : 'pts' }
}

export const pct = (value) => `${Math.round(value * 100)}%`

export const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
