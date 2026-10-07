// Segmented control switching between rule-based and AI-enhanced feedback.
import Icon from './Icon.jsx'

const OPTIONS = [
  { value: 'rules', label: 'Rules' },
  { value: 'ai', label: 'AI-Enhanced', icon: 'sparkles' },
]

export default function ModeToggle({ mode, onChange, busy }) {
  return (
    <div role="radiogroup" aria-label="Feedback mode" className="inline-flex h-9 items-center rounded-full border border-line bg-surface p-0.5">
      {OPTIONS.map((option) => {
        const active = mode === option.value
        return (
          <button key={option.value} type="button" role="radio" aria-checked={active} disabled={busy}
            onClick={() => onChange(option.value)}
            className={`focus-ring inline-flex h-8 items-center gap-1.5 rounded-full px-3.5 text-sm transition-all duration-200
              ${active ? 'bg-ink text-page' : 'text-ink-3 hover:text-ink'}`}>
            {option.icon && <Icon name={option.icon} className="size-3.5" />}
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
