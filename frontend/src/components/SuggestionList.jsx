// Prioritized suggestions as a quiet list; each row expands to show its evidence.
import { useId, useState } from 'react'
import Icon from './Icon.jsx'
import { PRIORITY, TONE, impactParts } from '../lib/format.js'

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'high', label: 'High' },
  { id: 'medium', label: 'Medium' },
  { id: 'low', label: 'Low' },
]

export default function SuggestionList({ feedback }) {
  const [filter, setFilter] = useState('all')
  const items = feedback.suggestions.filter((s) => filter === 'all' || s.priority === filter)
  const counts = { all: feedback.total, ...feedback.by_priority }

  if (!feedback.total) {
    return (
      <div className="py-16 text-center">
        <div className="mx-auto grid size-10 place-items-center rounded-full bg-good/10 text-good-ink">
          <Icon name="check" className="size-5" />
        </div>
        <p className="mt-4 font-medium text-ink">Nothing to fix</p>
        <p className="mt-1 text-sm text-ink-2">No rule found an improvement for this role.</p>
      </div>
    )
  }

  return (
    <div>
      <div role="group" aria-label="Filter by priority" className="mb-2 flex flex-wrap gap-1">
        {FILTERS.map((f) => (
          <button key={f.id} type="button" aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}
            className={`focus-ring h-8 rounded-full px-3 text-sm transition-colors
              ${filter === f.id ? 'bg-ink text-page' : 'text-ink-3 hover:bg-surface-2 hover:text-ink'}`}>
            {f.label} <span className="ml-0.5 tabular-nums opacity-60">{counts[f.id] ?? 0}</span>
          </button>
        ))}
      </div>

      {items.length ? (
        <ol className="divide-y divide-line">
          {items.map((item, index) => (
            <SuggestionRow key={`${item.rule_id}-${item.title}`} item={item} index={index} />
          ))}
        </ol>
      ) : (
        <p className="py-10 text-center text-sm text-ink-3">No suggestions at this priority.</p>
      )}
      {feedback.shown < feedback.total && (
        <p className="mt-4 text-xs text-ink-3">Showing the top {feedback.shown} of {feedback.total}.</p>
      )}
    </div>
  )
}

function SuggestionRow({ item, index }) {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const priority = PRIORITY[item.priority]
  const impact = impactParts(item.estimated_impact)

  return (
    <li className="animate-rise" style={{ animationDelay: `${Math.min(index, 8) * 35}ms` }}>
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls={panelId}
        className="focus-ring group -mx-3 flex w-[calc(100%+1.5rem)] items-start gap-5 rounded-2xl px-3 py-5 text-left transition-colors hover:bg-surface-2/60">
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2 text-xs text-ink-3">
            <span aria-hidden="true" className={`size-1.5 rounded-full ${TONE[priority.tone].dot}`} />
            <span className={TONE[priority.tone].ink}>{priority.label}</span>
            <span aria-hidden="true">·</span>
            <span className="capitalize">{item.category}</span>
          </p>
          <p className="mt-1.5 text-[15px] font-medium text-ink">{item.title}</p>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ink-2">{item.suggestion}</p>
        </div>
        <div className="flex shrink-0 items-center gap-4 pt-5">
          {impact && (
            <span className="text-right">
              <span className="block text-sm tabular-nums text-ink">{impact.value}</span>
              <span className="block text-[11px] text-ink-3">{impact.unit}</span>
            </span>
          )}
          <Icon name="chevron" className={`size-4 text-ink-3 transition-transform duration-300 group-hover:text-ink ${open ? 'rotate-180' : ''}`} />
        </div>
      </button>
      <div id={panelId} hidden={!open} className="pb-5">
        <div className="ml-0 border-l border-line-strong pl-4">
          <p className="eyebrow mb-2">Evidence</p>
          <ul className="space-y-1.5 text-sm text-ink-2">
            {item.evidence.map((line) => <li key={line} className="break-words">{line}</li>)}
          </ul>
          <p className="mt-3 font-mono text-[11px] text-ink-3">rule {item.rule_id}</p>
        </div>
      </div>
    </li>
  )
}
