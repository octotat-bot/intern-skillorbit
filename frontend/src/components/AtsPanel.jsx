// Skills tab: missing must-haves, matched requirements, nice-to-haves, ignored mentions.
import { StatusLabel } from './ui.jsx'

export default function AtsPanel({ ats }) {
  return (
    <div className="grid gap-12 lg:grid-cols-2">
      <section>
        <Heading title="Missing must-haves" count={ats.missing_must_have.length}
          note={`Requirements typical ${ats.role_name} postings expect`} />
        {ats.missing_must_have.length ? (
          <ul className="divide-y divide-line">
            {ats.missing_must_have.map((m) => (
              <li key={m.label} className="flex items-start justify-between gap-4 py-3.5">
                <div className="min-w-0">
                  <StatusLabel tone="critical" className="!text-ink">{m.label}</StatusLabel>
                  <p className="mt-1 pl-3 text-xs text-ink-3">Accepted: {m.alternatives.join(', ')}</p>
                </div>
                <span className="shrink-0 text-xs tabular-nums text-ink-3">weight {m.weight}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="py-3.5 text-sm text-ink-2">Every must-have requirement is covered.</p>
        )}
      </section>

      <section>
        <Heading title="Matched" count={ats.matched.length} note="Where each requirement was found" />
        {ats.matched.length ? (
          <ul className="divide-y divide-line">
            {ats.matched.map((m) => (
              <li key={m.label} className="flex items-start justify-between gap-4 py-3.5">
                <div className="min-w-0">
                  <StatusLabel tone="good" className="!text-ink">{m.label}</StatusLabel>
                  <p className="mt-1 pl-3 text-xs text-ink-3">
                    {m.found_as.join(', ')} <span aria-hidden="true">·</span> {m.sections.join(', ')}
                  </p>
                </div>
                <span className="shrink-0 text-xs text-ink-3">{m.type === 'must_have' ? 'must-have' : 'bonus'}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="py-3.5 text-sm text-ink-2">No role requirements matched yet.</p>
        )}
      </section>

      <section className="lg:col-span-2">
        <Heading title="Worth adding" count={ats.missing_nice_to_have.length} note="Bonus skills, only if you have them" />
        {ats.missing_nice_to_have.length ? (
          <ul className="flex flex-wrap gap-2">
            {ats.missing_nice_to_have.map((m) => (
              <li key={m.label} className="rounded-full border border-line px-3 py-1 text-sm text-ink-2">{m.label}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-ink-2">All bonus skills found.</p>
        )}
        {ats.ignored.length > 0 && (
          <p className="mt-6 text-xs leading-relaxed text-ink-3">
            Not counted: {ats.ignored.map((i) => `${i.surface} (${i.reason.toLowerCase()})`).join('; ')}.
          </p>
        )}
      </section>
    </div>
  )
}

function Heading({ title, count, note }) {
  return (
    <header className="mb-3">
      <h3 className="flex items-baseline gap-2 text-[15px] font-medium text-ink">
        {title} <span className="text-sm tabular-nums text-ink-3">{count}</span>
      </h3>
      <p className="mt-0.5 text-xs text-ink-3">{note}</p>
    </header>
  )
}
