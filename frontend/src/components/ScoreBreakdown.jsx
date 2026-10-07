// Every scoring check with points and evidence: the table view behind the chart.
import { useState } from 'react'
import Icon from './Icon.jsx'

const STATUS = {
  pass: { dot: 'bg-good', label: 'Earned' },
  partial: { dot: 'bg-warning', label: 'Partly earned' },
  fail: { dot: 'bg-critical', label: 'Missed' },
}

export default function ScoreBreakdown({ parameters }) {
  const [open, setOpen] = useState(Object.keys(parameters)[0])
  return (
    <div className="divide-y divide-line border-y border-line">
      {Object.entries(parameters).map(([key, p]) => {
        const expanded = open === key
        return (
          <section key={key}>
            <h3>
              <button type="button" onClick={() => setOpen(expanded ? null : key)} aria-expanded={expanded}
                aria-controls={`breakdown-${key}`}
                className="focus-ring group flex w-full items-center justify-between gap-4 rounded-lg py-5 text-left">
                <span className="text-[15px] font-medium text-ink">{p.label}</span>
                <span className="flex items-center gap-4">
                  <span className="text-sm tabular-nums text-ink">{p.score}<span className="text-ink-3"> / {p.max}</span></span>
                  <Icon name="chevron" className={`size-4 text-ink-3 transition-transform duration-300 group-hover:text-ink ${expanded ? 'rotate-180' : ''}`} />
                </span>
              </button>
            </h3>
            <div id={`breakdown-${key}`} hidden={!expanded} className="pb-6">
              <table className="w-full text-sm">
                <caption className="sr-only">{p.label} checks</caption>
                <thead className="text-left">
                  <tr className="text-xs text-ink-3">
                    <th scope="col" className="pb-2 pr-4 font-normal">Check</th>
                    <th scope="col" className="pb-2 pr-4 font-normal">Evidence</th>
                    <th scope="col" className="pb-2 text-right font-normal">Points</th>
                  </tr>
                </thead>
                <tbody className="align-top">
                  {p.evidence.map((check) => (
                    <tr key={check.id} className="border-t border-line/70">
                      <td className="py-2.5 pr-4">
                        <span className="inline-flex items-center gap-2 text-ink">
                          <span className={`size-1.5 shrink-0 rounded-full ${STATUS[check.status].dot}`} aria-hidden="true" />
                          <span>{check.label}</span>
                          <span className="sr-only">({STATUS[check.status].label})</span>
                        </span>
                      </td>
                      <td className="break-words py-2.5 pr-4 text-ink-2">{check.detail}</td>
                      <td className="whitespace-nowrap py-2.5 text-right tabular-nums text-ink">
                        {check.points}<span className="text-ink-3"> / {check.max}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )
      })}
    </div>
  )
}
