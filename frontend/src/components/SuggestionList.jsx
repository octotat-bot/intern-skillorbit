// Prioritized suggestions with a priority filter; each card expands to show evidence.
import { useId, useState } from 'react'
import Icon from './Icon.jsx'
import { Card, StatusBadge } from './ui.jsx'
import { PRIORITY, impactLabel } from '../lib/format.js'

const FILTERS = ['all', 'high', 'medium', 'low']

export default function SuggestionList({ feedback }) {
  const [filter, setFilter] = useState('all')
  const items = feedback.suggestions.filter((s) => filter === 'all' || s.priority === filter)
  const counts = { all: feedback.total, ...feedback.by_priority }

  return (
    <Card title="Improvement suggestions"
      subtitle={feedback.total ? `${feedback.total} found, sorted by priority and estimated impact` : 'Nothing to fix'}>
      <div role="group" aria-label="Filter by priority" className="mb-4 flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)}
            className={`focus-ring rounded-lg border px-2.5 py-1 text-xs font-medium capitalize transition
              ${filter === f ? 'border-accent bg-accent/15 text-ink' : 'border-line text-ink-3 hover:text-ink'}`}>
            {f} <span className="tabular-nums text-ink-3">{counts[f] ?? 0}</span>
          </button>
        ))}
      </div>
      {items.length ? (
        <ol className="space-y-2">
          {items.map((item, index) => <SuggestionCard key={`${item.rule_id}-${item.title}`} item={item} index={index} />)}
        </ol>
      ) : (
        <p className="rounded-lg bg-card-2 p-4 text-sm text-ink-2">
          {feedback.total ? 'No suggestions at this priority.' : 'Great work. No rule found anything to improve.'}
        </p>
      )}
      {feedback.shown < feedback.total && (
        <p className="mt-3 text-xs text-ink-3">Showing the top {feedback.shown} of {feedback.total}.</p>
      )}
    </Card>
  )
}

function SuggestionCard({ item, index }) {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const priority = PRIORITY[item.priority]
  const impact = impactLabel(item.estimated_impact)

  return (
    <li className="animate-rise overflow-hidden rounded-xl border border-line bg-card-2/60 transition hover:border-ink-3/60"
      style={{ animationDelay: `${Math.min(index, 10) * 30}ms` }}>
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls={panelId}
        className="focus-ring flex w-full items-start gap-3 rounded-xl p-3.5 text-left">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={priority.tone} icon={priority.icon}>{priority.label}</StatusBadge>
            {impact && <span className="text-xs font-medium text-ink-3 tabular-nums">{impact}</span>}
            <span className="text-xs text-ink-3">{item.rule_id}</span>
          </div>
          <p className="mt-1.5 font-medium text-ink">{item.title}</p>
          <p className="mt-0.5 text-sm text-ink-2">{item.suggestion}</p>
        </div>
        <Icon name="chevron" className={`mt-1 size-4 shrink-0 text-ink-3 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      <div id={panelId} hidden={!open} className="border-t border-line px-3.5 py-3">
        <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-3">Evidence</p>
        <ul className="space-y-1 text-sm text-ink-2">
          {item.evidence.map((line) => (
            <li key={line} className="flex gap-2"><span aria-hidden="true" className="text-ink-3">›</span><span className="break-words">{line}</span></li>
          ))}
        </ul>
      </div>
    </li>
  )
}
