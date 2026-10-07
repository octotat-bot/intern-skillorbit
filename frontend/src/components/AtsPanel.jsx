// ATS keyword-match card: score, coverage meters, matched vs missing skills.
import { useState } from 'react'
import Icon from './Icon.jsx'
import ScoreRing from './ScoreRing.jsx'
import { Card, Chip, Meter } from './ui.jsx'
import { pct } from '../lib/format.js'

export default function AtsPanel({ ats }) {
  const [showDetail, setShowDetail] = useState(false)
  const must = ats.matched.filter((m) => m.type === 'must_have')
  const nice = ats.matched.filter((m) => m.type === 'nice_to_have')

  return (
    <Card title="ATS keyword match" subtitle={`Against typical ${ats.role_name} requirements`}>
      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
        <ScoreRing value={ats.ats_score} label="ATS score" size={128} stroke={10} />
        <div className="w-full flex-1 space-y-3">
          <Meter label="Must-have coverage" value={ats.must_have_coverage} tone="neutral" valueLabel={pct(ats.must_have_coverage)} />
          <Meter label="Nice-to-have coverage" value={ats.nice_to_have_coverage} tone="neutral" valueLabel={pct(ats.nice_to_have_coverage)} />
          <Meter label="Wording similarity to role" value={ats.tfidf.score} max={100} tone="neutral"
            valueLabel={`${Math.round(ats.tfidf.score)}%`} />
          <button type="button" onClick={() => setShowDetail((v) => !v)} aria-expanded={showDetail}
            className="focus-ring inline-flex items-center gap-1 rounded text-xs font-medium text-accent-ink hover:underline">
            How is this calculated?
            <Icon name="chevron" className={`size-3.5 transition-transform ${showDetail ? 'rotate-180' : ''}`} />
          </button>
          {showDetail && (
            <div className="animate-rise rounded-lg bg-card-2 p-3 text-xs leading-relaxed text-ink-2">
              Keyword score {ats.keyword_score} (70% must-have, 30% nice-to-have) blended 80/20 with
              text similarity {ats.tfidf.score}, minus a formatting penalty of {ats.format_penalty.points} ({ats.format_penalty.detail}).
              This is a transparent heuristic, not a vendor-verified ATS result.
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <SkillGroup title="Missing must-have skills" empty="None. Every must-have requirement is covered."
          items={ats.missing_must_have.map((m) => ({ key: m.label, label: m.label, title: `Accepted: ${m.alternatives.join(', ')}` }))}
          variant="missing" />
        <SkillGroup title="Matched requirements" empty="No role requirements matched yet."
          items={[...must, ...nice].map((m) => ({ key: m.label, label: m.label, title: `Found as ${m.found_as.join(', ')} in ${m.sections.join(', ')}` }))}
          variant="matched" />
        <SkillGroup title="Nice-to-have skills to consider" empty="All nice-to-have skills found."
          items={ats.missing_nice_to_have.map((m) => ({ key: m.label, label: m.label }))} variant="neutral" />
        {ats.ignored.length > 0 && (
          <p className="text-xs text-ink-3">
            Not counted: {ats.ignored.map((i) => `${i.surface} (${i.reason.toLowerCase()})`).join('; ')}.
          </p>
        )}
      </div>
    </Card>
  )
}

function SkillGroup({ title, items, variant, empty }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-3">
        {title} <span className="font-normal normal-case">({items.length})</span>
      </h3>
      {items.length ? (
        <ul className="flex flex-wrap gap-1.5">
          {items.map((item) => <Chip key={item.key} variant={variant} title={item.title}>{item.label}</Chip>)}
        </ul>
      ) : (
        <p className="text-sm text-ink-3">{empty}</p>
      )}
    </div>
  )
}
