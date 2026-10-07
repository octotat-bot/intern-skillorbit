// AI-enhanced (RAG) feedback: rewrites, skill-gap explanations and citations,
// or a clear notice plus the retrieved guidance when the AI layer is unavailable.
import { createContext, useContext, useState } from 'react'
import Icon from './Icon.jsx'
import { Skeleton } from './ui.jsx'

// Lets a citation anywhere in the panel open the source list and jump to its chunk.
const RevealContext = createContext(() => {})

export default function AiFeedbackPanel({ analysis, loading }) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const reveal = (id) => {
    setSourcesOpen(true)
    requestAnimationFrame(() => {
      const target = document.getElementById(`chunk-${id}`)
      target?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      target?.focus({ preventScroll: true })
    })
  }

  if (loading) {
    return (
      <section className="panel p-6 sm:p-8" aria-busy="true" aria-label="Generating AI insights">
        <Header subtitle="Retrieving guidance and generating suggestions..." />
        <div className="mt-6 space-y-3"><Skeleton className="h-4 w-2/3" /><Skeleton className="h-14" /><Skeleton className="h-14" /></div>
      </section>
    )
  }
  if (!analysis) return null
  const generated = analysis.generated_feedback
  const context = analysis.retrieved_context || []

  return (
    <RevealContext.Provider value={reveal}>
      <section className="panel p-6 sm:p-8">
        <Header subtitle={generated ? `${generated.model} · grounded only in the cited sources` : 'Optional layer on top of the rule-based results'} />

        {!analysis.ai_available && (
          <div role="status" className="mt-6 flex items-start gap-3 rounded-2xl bg-surface-2 p-4 text-sm">
            <Icon name="info" className="mt-0.5 size-4 shrink-0 text-ink-3" />
            <p className="text-ink-2">
              <span className="text-ink">AI suggestions are unavailable.</span> {analysis.ai_unavailable_reason}.
              Your score and rule-based suggestions are unaffected.
            </p>
          </div>
        )}

        {generated && (
          <div className="mt-8 space-y-10">
            {generated.summary && (
              <p className="max-w-3xl font-serif text-2xl leading-snug text-ink">
                {generated.summary.text} <Citations ids={generated.summary.chunk_ids} />
              </p>
            )}
            {generated.bullet_rewrites.length > 0 && (
              <div>
                <p className="eyebrow mb-4">Bullet rewrites</p>
                <ul className="divide-y divide-line">
                  {generated.bullet_rewrites.map((r) => (
                    <li key={r.original} className="grid gap-2 py-4 text-sm sm:grid-cols-2 sm:gap-8">
                      <p className="text-ink-3 line-through decoration-line-strong">{r.original}</p>
                      <p className="text-ink">{r.rewritten} <Citations ids={r.chunk_ids} /></p>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-xs text-ink-3">Bracketed placeholders like [X%] mark numbers only you know.</p>
              </div>
            )}
            {generated.skill_gaps.length > 0 && (
              <div>
                <p className="eyebrow mb-4">Skill gaps</p>
                <dl className="divide-y divide-line">
                  {generated.skill_gaps.map((g) => (
                    <div key={g.skill} className="grid gap-1 py-4 text-sm sm:grid-cols-[180px_1fr] sm:gap-8">
                      <dt className="font-medium text-ink">{g.skill}</dt>
                      <dd className="text-ink-2">{g.explanation} <Citations ids={g.chunk_ids} /></dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
            {generated.dropped_items > 0 && (
              <p className="text-xs text-ink-3">{generated.dropped_items} generated item(s) were discarded for not citing the retrieved sources.</p>
            )}
          </div>
        )}

        {context.length > 0 && (
          <Sources chunks={context} cited={new Set(generated?.citations || [])}
            open={sourcesOpen} onToggle={() => setSourcesOpen((v) => !v)} />
        )}
      </section>
    </RevealContext.Provider>
  )
}

function Header({ subtitle }) {
  return (
    <header className="flex items-start gap-3">
      <span className="grid size-8 shrink-0 place-items-center rounded-full bg-accent/10 text-accent-ink">
        <Icon name="sparkles" className="size-4" />
      </span>
      <div>
        <h2 className="text-[15px] font-medium text-ink">AI insights</h2>
        <p className="mt-0.5 text-sm text-ink-3">{subtitle}</p>
      </div>
    </header>
  )
}

function Citations({ ids }) {
  const reveal = useContext(RevealContext)
  return (
    <span className="inline-flex flex-wrap gap-1 align-middle font-sans">
      {ids.map((id) => (
        <a key={id} href={`#chunk-${id}`} onClick={(e) => { e.preventDefault(); reveal(id) }} aria-label={`Source ${id}`}
          className="focus-ring rounded-md border border-line px-1.5 py-0.5 font-mono text-[10px] text-ink-3 transition-colors hover:border-line-strong hover:text-ink">
          {id}
        </a>
      ))}
    </span>
  )
}

function Sources({ chunks, cited, open, onToggle }) {
  return (
    <div className="mt-8 border-t border-line pt-5">
      <button type="button" onClick={onToggle} aria-expanded={open} aria-controls="ai-sources"
        className="focus-ring group flex w-full items-center justify-between rounded-lg text-left text-sm">
        <span className="inline-flex items-center gap-2 text-ink-2 group-hover:text-ink">
          <Icon name="book" className="size-4" /> Retrieved guidance · {chunks.length} sources
        </span>
        <Icon name="chevron" className={`size-4 text-ink-3 transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
      </button>
      <ul id="ai-sources" hidden={!open} className="mt-4 divide-y divide-line">
        {chunks.map((c) => (
          <li key={c.id} id={`chunk-${c.id}`} tabIndex={-1} className="focus-ring scroll-mt-24 rounded-lg py-4 text-sm">
            <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="font-mono text-[11px] text-ink-3">{c.id}</span>
              <span className="font-medium text-ink">{c.title}</span>
              {cited.has(c.id) && <span className="text-xs text-accent-ink">cited</span>}
            </p>
            <p className="mt-1.5 leading-relaxed text-ink-2">{c.text}</p>
            <p className="mt-1.5 text-xs text-ink-3">{c.source} · relevance {c.score.toFixed(2)}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
