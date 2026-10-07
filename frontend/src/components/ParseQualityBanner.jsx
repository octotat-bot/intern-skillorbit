// Warning banner shown when the file has ATS formatting risks.
import Icon from './Icon.jsx'

export default function ParseQualityBanner({ quality }) {
  if (!quality?.ats_risk) return null
  const severe = quality.level === 'poor'
  return (
    <section role="status" aria-live="polite"
      className={`animate-rise rounded-2xl border p-4 sm:p-5 ${severe ? 'border-critical/50 bg-critical/10' : 'border-warning/50 bg-warning/10'}`}>
      <div className="flex items-start gap-3">
        <Icon name="alert" className={`mt-0.5 size-5 shrink-0 ${severe ? 'text-critical-ink' : 'text-warning-ink'}`} />
        <div className="min-w-0">
          <h2 className="font-semibold text-ink">
            ATS formatting risk: parse quality {quality.level} ({quality.score}/100)
          </h2>
          <p className="mt-0.5 text-sm text-ink-2">
            Applicant tracking systems may misread this file. This also lowers the ATS score below.
          </p>
          <ul className="mt-2 space-y-1 text-sm text-ink-2">
            {quality.issues.map((issue) => (
              <li key={issue.code} className="flex gap-2">
                <span aria-hidden="true">•</span>
                <span><span className="font-medium text-ink">{issue.message}</span> <span className="text-ink-3">({issue.evidence})</span></span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
