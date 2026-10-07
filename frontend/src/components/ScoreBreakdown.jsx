// Every scoring check with points and evidence: the table view behind the chart.
import { useState } from 'react'
import Icon from './Icon.jsx'
import { Card } from './ui.jsx'

const STATUS = {
  pass: { icon: 'check', className: 'text-good-ink', label: 'Pass' },
  partial: { icon: 'info', className: 'text-warning-ink', label: 'Partial' },
  fail: { icon: 'x', className: 'text-critical-ink', label: 'Missed' },
}

export default function ScoreBreakdown({ parameters }) {
  const [open, setOpen] = useState(null)
  return (
    <Card title="Score breakdown" subtitle="Every point, with the evidence that earned or lost it">
      <div className="divide-y divide-line">
        {Object.entries(parameters).map(([key, p]) => {
          const expanded = open === key
          return (
            <div key={key}>
              <button type="button" onClick={() => setOpen(expanded ? null : key)} aria-expanded={expanded}
                aria-controls={`breakdown-${key}`}
                className="focus-ring flex w-full items-center justify-between gap-3 rounded-lg py-3 text-left">
                <span className="font-medium text-ink">{p.label}</span>
                <span className="flex items-center gap-3">
                  <span className="text-sm font-semibold tabular-nums text-ink">{p.score}<span className="font-normal text-ink-3"> / {p.max}</span></span>
                  <Icon name="chevron" className={`size-4 text-ink-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
                </span>
              </button>
              <div id={`breakdown-${key}`} hidden={!expanded} className="pb-3">
                <table className="w-full text-sm">
                  <caption className="sr-only">{p.label} checks</caption>
                  <thead className="text-left text-xs text-ink-3">
                    <tr><th className="py-1 pr-2 font-medium">Check</th><th className="py-1 pr-2 font-medium">Evidence</th><th className="py-1 text-right font-medium">Points</th></tr>
                  </thead>
                  <tbody>
                    {p.evidence.map((check) => {
                      const s = STATUS[check.status]
                      return (
                        <tr key={check.id} className="align-top">
                          <td className="py-1.5 pr-2">
                            <span className={`inline-flex items-center gap-1.5 ${s.className}`}>
                              <Icon name={s.icon} className="size-3.5 shrink-0" title={s.label} />
                              <span className="text-ink">{check.label}</span>
                            </span>
                          </td>
                          <td className="py-1.5 pr-2 text-ink-2 break-words">{check.detail}</td>
                          <td className="py-1.5 text-right tabular-nums text-ink whitespace-nowrap">{check.points} / {check.max}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
