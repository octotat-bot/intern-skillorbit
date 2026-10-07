import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import AiFeedbackPanel from '../components/AiFeedbackPanel.jsx'
import AtsPanel from '../components/AtsPanel.jsx'
import Icon from '../components/Icon.jsx'
import ModeToggle from '../components/ModeToggle.jsx'
import ParseQualityBanner from '../components/ParseQualityBanner.jsx'
import ScoreBreakdown from '../components/ScoreBreakdown.jsx'
import ScoreRing from '../components/ScoreRing.jsx'
import SubScoreChart from '../components/SubScoreChart.jsx'
import SuggestionList from '../components/SuggestionList.jsx'
import Tabs from '../components/Tabs.jsx'
import { ErrorState, Meter, Skeleton, StatusLabel } from '../components/ui.jsx'
import { downloadReport, errorMessage, fetchAnalysis, fetchRoles } from '../api/client.js'
import { useCountUp } from '../hooks/useCountUp.js'
import { pct, plural, scoreStatus } from '../lib/format.js'

export default function DashboardPage() {
  const { resumeId } = useParams()
  const [params, setParams] = useSearchParams()
  const role = params.get('role') || ''
  const mode = params.get('mode') === 'ai' ? 'ai' : 'rules'

  const tab = params.get('tab') || 'improvements'
  const [roles, setRoles] = useState([])
  const [state, setState] = useState({ status: 'loading', data: null, error: null })
  const cache = useRef(new Map())   // "role|mode" -> analysis, so switching back is instant

  const load = useCallback(async () => {
    const key = `${role}|${mode}`
    if (cache.current.has(key)) {
      setState({ status: 'ready', data: cache.current.get(key), error: null })
      return
    }
    setState((s) => ({ status: s.data ? 'refreshing' : 'loading', data: s.data, error: null }))
    try {
      const data = await fetchAnalysis(resumeId, role, mode)
      cache.current.set(key, data)
      setState({ status: 'ready', data, error: null })
    } catch (err) {
      setState({ status: 'error', data: null, error: errorMessage(err) })
    }
  }, [resumeId, role, mode])

  useEffect(() => { load() }, [load])
  useEffect(() => { fetchRoles().then(setRoles).catch(() => setRoles([])) }, [])

  // Role, mode and tab live in the URL, so every view is linkable; tab changes don't add history entries.
  const update = (changes) => setParams((p) => {
    const next = new URLSearchParams(p)
    Object.entries(changes).forEach(([k, v]) => next.set(k, v))
    return next
  }, { replace: 'tab' in changes })

  if (state.status === 'loading') return <DashboardSkeleton />
  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-2xl px-4 py-24 sm:px-8">
        <ErrorState title="Couldn't load the analysis" message={state.error} onRetry={load}>
          <Link to="/" className="btn-ghost !h-10">Upload another resume</Link>
        </ErrorState>
      </div>
    )
  }

  const a = state.data
  const refreshing = state.status === 'refreshing'
  const { feedback } = a
  const tabs = [
    { id: 'improvements', label: 'Improvements', count: feedback.total, content: <SuggestionList feedback={feedback} /> },
    { id: 'skills', label: 'Skills match', count: a.ats.missing_must_have.length || undefined, content: <AtsPanel ats={a.ats} /> },
    { id: 'details', label: 'Score details', content: <ScoreBreakdown parameters={a.score.parameters} /> },
  ]

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 pb-8 pt-8 sm:px-8 sm:pt-12">
      <header className="animate-rise flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <Link to="/" className="focus-ring -ml-1 inline-flex items-center gap-1.5 rounded-full px-1 text-sm text-ink-3 transition-colors hover:text-ink">
            <Icon name="arrowLeft" className="size-3.5" /> New analysis
          </Link>
          <h1 className="mt-4 truncate text-3xl font-medium tracking-[-0.03em] text-ink" title={a.filename}>{a.filename}</h1>
          <p className="mt-1.5 text-sm text-ink-3">
            {a.contact.name && <>{a.contact.name} <span aria-hidden="true">·</span> </>}
            {plural(a.sections_detected.length, 'section')} detected
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="relative">
            <span className="sr-only">Target role</span>
            <select value={role} onChange={(e) => update({ role: e.target.value })} disabled={refreshing}
              className="focus-ring h-9 appearance-none rounded-full border border-line bg-surface py-0 pl-4 pr-9 text-sm text-ink transition-colors hover:border-line-strong">
              {(roles.length ? roles : [a.role]).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
            <Icon name="chevron" className="pointer-events-none absolute right-3 top-1/2 size-3.5 -translate-y-1/2 text-ink-3" />
          </label>
          <ModeToggle mode={mode} onChange={(m) => update({ mode: m })} busy={refreshing} />
          <ReportButton resumeId={resumeId} role={role} mode={mode} />
        </div>
      </header>

      <ParseQualityBanner quality={a.parse_quality} />

      <section aria-label="Overview" aria-busy={refreshing}
        className={`panel animate-rise grid transition-opacity duration-300 [animation-delay:80ms] lg:grid-cols-[0.9fr_1fr_1.25fr]
          divide-y divide-line lg:divide-x lg:divide-y-0 ${refreshing ? 'opacity-50' : ''}`}>
        <div className="flex flex-col items-center justify-center px-6 py-10">
          <p className="eyebrow mb-6">Resume score</p>
          <ScoreRing value={a.score.total} label="Resume score" band={a.score.band} />
          <p className="mt-4 max-w-[16rem] text-center text-sm text-ink-3">
            {feedback.total
              ? `${plural(feedback.total, 'suggestion')}, ${feedback.by_priority.high} high priority`
              : 'Nothing left to fix'}
          </p>
        </div>
        <AtsSummary ats={a.ats} />
        <div className="px-6 py-10 sm:px-8">
          <p className="eyebrow mb-6">Breakdown</p>
          <SubScoreChart parameters={a.score.parameters} />
        </div>
      </section>

      {mode === 'ai' && <AiFeedbackPanel analysis={refreshing ? null : a} loading={refreshing} />}

      <section aria-label="Details" className="pt-4">
        <Tabs label="Analysis details" tabs={tabs} active={tab} onChange={(id) => update({ tab: id })} />
      </section>
    </div>
  )
}

/** Downloads the PDF report for the current role and mode. */
function ReportButton({ resumeId, role, mode }) {
  const [state, setState] = useState({ busy: false, error: null })
  const download = async () => {
    setState({ busy: true, error: null })
    try {
      await downloadReport(resumeId, role, mode)
      setState({ busy: false, error: null })
    } catch (err) {
      setState({ busy: false, error: errorMessage(err) })
    }
  }
  return (
    <div className="relative">
      <button type="button" onClick={download} disabled={state.busy} aria-busy={state.busy}
        className="focus-ring inline-flex h-9 items-center gap-2 rounded-full bg-ink px-4 text-sm font-medium text-page transition hover:opacity-90 active:scale-[.98] disabled:opacity-50">
        <Icon name="download" className="size-4" />
        {state.busy ? 'Preparing...' : 'Report'}
      </button>
      {state.error && (
        <p role="alert" className="absolute right-0 top-11 z-10 w-64 rounded-xl border border-line bg-surface p-3 text-xs text-critical-ink shadow-xl">
          {state.error}
        </p>
      )}
    </div>
  )
}

function AtsSummary({ ats }) {
  const [explain, setExplain] = useState(false)
  const shown = useCountUp(ats.ats_score)
  const status = scoreStatus(ats.ats_score)
  return (
    <div className="px-6 py-10 sm:px-8">
      <p className="eyebrow">ATS match · {ats.role_name}</p>
      <div className="mt-6 flex items-end gap-3">
        <span className="text-5xl font-light leading-none tracking-[-0.04em] text-ink">{shown}</span>
        <span className="pb-1 text-sm text-ink-3">/ 100</span>
        <StatusLabel tone={status.tone} className="ml-auto pb-1">{status.label}</StatusLabel>
      </div>
      <div className="mt-8 space-y-5">
        <Meter label="Must-have skills" value={ats.must_have_coverage} valueLabel={pct(ats.must_have_coverage)} />
        <Meter label="Bonus skills" value={ats.nice_to_have_coverage} valueLabel={pct(ats.nice_to_have_coverage)} />
        <Meter label="Wording match" value={ats.tfidf.score} max={100} valueLabel={`${Math.round(ats.tfidf.score)}%`} />
      </div>
      <button type="button" onClick={() => setExplain((v) => !v)} aria-expanded={explain}
        className="focus-ring mt-6 rounded text-xs text-ink-3 underline decoration-line-strong underline-offset-4 transition-colors hover:text-ink">
        How is this calculated?
      </button>
      {explain && (
        <p className="animate-rise mt-3 text-xs leading-relaxed text-ink-3">
          Keyword score {ats.keyword_score} (70% must-have, 30% bonus) blended 80/20 with wording similarity
          {' '}{ats.tfidf.score}, minus {ats.format_penalty.points} for formatting ({ats.format_penalty.detail}).
          A transparent heuristic, not a vendor-verified ATS result.
        </p>
      )}
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 pt-12 sm:px-8" aria-busy="true" aria-label="Loading analysis">
      <div className="space-y-3"><Skeleton className="h-3 w-24" /><Skeleton className="h-8 w-72" /><Skeleton className="h-3 w-40" /></div>
      <Skeleton className="h-[380px] !rounded-3xl" />
      <div className="space-y-4"><Skeleton className="h-8 w-80" /><Skeleton className="h-20" /><Skeleton className="h-20" /></div>
    </div>
  )
}
