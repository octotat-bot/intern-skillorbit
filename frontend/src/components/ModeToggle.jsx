// Segmented control switching between rule-based and AI-enhanced feedback.
import Icon from './Icon.jsx'

const OPTIONS = [
  { value: 'rules', label: 'Rules', icon: 'check' },
  { value: 'ai', label: 'AI-Enhanced', icon: 'sparkles' },
]

export default function ModeToggle({ mode, onChange, busy }) {
  return (
    <div role="radiogroup" aria-label="Feedback mode" className="inline-flex rounded-xl border border-line bg-card-2 p-1">
      {OPTIONS.map((option) => {
        const active = mode === option.value
        return (
          <button key={option.value} type="button" role="radio" aria-checked={active} disabled={busy}
            onClick={() => onChange(option.value)}
            className={`focus-ring inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition
              ${active ? 'bg-card text-ink shadow-sm' : 'text-ink-3 hover:text-ink'}`}>
            <Icon name={option.icon} className="size-4" />
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
