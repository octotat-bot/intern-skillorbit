// Accessible tabs (WAI-ARIA pattern): arrow keys move between tabs, Home/End jump.
import { useId, useRef } from 'react'

export default function Tabs({ tabs, active, onChange, label }) {
  const baseId = useId()
  const refs = useRef([])

  const onKeyDown = (event, index) => {
    const last = tabs.length - 1
    const next = { ArrowRight: index === last ? 0 : index + 1, ArrowLeft: index === 0 ? last : index - 1,
      Home: 0, End: last }[event.key]
    if (next === undefined) return
    event.preventDefault()
    onChange(tabs[next].id)
    refs.current[next]?.focus()
  }

  const current = tabs.find((t) => t.id === active) || tabs[0]
  return (
    <div>
      <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto border-b border-line">
        {tabs.map((tab, index) => {
          const selected = tab.id === current.id
          return (
            <button key={tab.id} ref={(el) => { refs.current[index] = el }} type="button" role="tab"
              id={`${baseId}-tab-${tab.id}`} aria-selected={selected} aria-controls={`${baseId}-panel-${tab.id}`}
              tabIndex={selected ? 0 : -1} onClick={() => onChange(tab.id)} onKeyDown={(e) => onKeyDown(e, index)}
              className={`focus-ring relative -mb-px flex shrink-0 items-center gap-2 rounded-t-lg px-3 pb-3 pt-2 text-sm transition-colors
                ${selected ? 'text-ink' : 'text-ink-3 hover:text-ink-2'}`}>
              {tab.label}
              {tab.count !== undefined && (
                <span className={`rounded-full px-1.5 text-xs tabular-nums ${selected ? 'bg-surface-2 text-ink-2' : 'text-ink-3'}`}>
                  {tab.count}
                </span>
              )}
              <span aria-hidden="true"
                className={`absolute inset-x-2 bottom-0 h-px transition-opacity ${selected ? 'bg-ink opacity-100' : 'opacity-0'}`} />
            </button>
          )
        })}
      </div>
      <div role="tabpanel" id={`${baseId}-panel-${current.id}`} aria-labelledby={`${baseId}-tab-${current.id}`}
        tabIndex={0} className="focus-ring rounded-lg pt-8" key={current.id}>
        <div className="animate-rise">{current.content}</div>
      </div>
    </div>
  )
}
