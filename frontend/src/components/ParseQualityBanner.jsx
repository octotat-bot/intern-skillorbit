// Slim notice shown when the file has ATS formatting risks.
import { useState } from 'react'
import Icon from './Icon.jsx'

export default function ParseQualityBanner({ quality }) {
  const [open, setOpen] = useState(false)
  if (!quality?.ats_risk) return null
  const severe = quality.level === 'poor'
  const first = quality.issues[0]

  return (
    <section role="status" aria-live="polite"
      className={`animate-rise rounded-2xl border px-4 py-3.5 sm:px-5 ${severe ? 'border-critical/30 bg-critical/[0.06]' : 'border-warning/30 bg-warning/[0.06]'}`}>
      <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
        <Icon name="alert" className={`mt-0.5 size-4 shrink-0 ${severe ? 'text-critical-ink' : 'text-warning-ink'}`} />
        <div className="min-w-0 flex-1 text-sm">
          <p className="text-ink">
            <span className="font-medium">Formatting risk</span>
            <span className="text-ink-2"> · parse quality {quality.level} ({quality.score}/100). {first?.message}</span>
          </p>
          {open && (
            <ul className="mt-2 space-y-1 text-ink-2">
              {quality.issues.map((issue) => (
                <li key={issue.code}>{issue.message} <span className="text-ink-3">{issue.evidence}</span></li>
              ))}
              <li className="text-ink-3">This lowers the ATS score; the resume score is unaffected.</li>
            </ul>
          )}
        </div>
        <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}
          className="focus-ring shrink-0 rounded text-sm text-ink-2 underline-offset-4 hover:text-ink hover:underline">
          {open ? 'Hide details' : 'Details'}
        </button>
      </div>
    </section>
  )
}
