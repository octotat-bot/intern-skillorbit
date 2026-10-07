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
import { Card, ErrorState, Skeleton } from '../components/ui.jsx'
import { errorMessage, fetchAnalysis, fetchRoles } from '../api/client.js'

export default function DashboardPage() {
  const { resumeId } = useParams()
  const [params, setParams] = useSearchParams()
  const role = params.get('role') || ''
  const mode = params.get('mode') === 'ai' ? 'ai' : 'rules'

  const [roles, setRoles] = useState([])
  const [state, setState] = useState({ status: 'loading', data: null, error: null })
  const cache = useRef(new Map())   // "role|mode" -> analysis, so toggling is instant

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

  const update = (changes) => setParams((p) => {
    const next = new URLSearchParams(p)
    Object.entries(changes).forEach(([k, v]) => next.set(k, v))
    return next
  })

  if (state.status === 'loading') return <DashboardSkeleton />
  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <ErrorState title="Couldn't load the analysis" message={state.error} onRetry={load}>
          <Link to="/" className="btn-secondary"><Icon name="arrowLeft" className="size-4" /> Upload another resume</Link>
        </ErrorState>
      </div>
    )
  }

  const a = state.data
  const refreshing = state.status === 'refreshing'
  const high = a.feedback.by_priority.high
  return (
    <div className="mx-auto max-w-7xl min-w-0 space-y-6 px-4 py-6 sm:px-6 sm:py-8">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <Link to="/" className="focus-ring inline-flex items-center gap-1 rounded text-sm text-ink-3 hover:text-ink">
            <Icon name="arrowLeft" className="size-4" /> New analysis
          </Link>
          <h1 className="mt-2 truncate text-2xl font-semibold tracking-tight text-ink" title={a.filename}>{a.filename}</h1>
          <p className="text-sm text-ink-3">
            {a.contact.name ? `${a.contact.name} · ` : ''}{a.sections_detected.length} sections detected
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex min-w-0 items-center gap-2 text-sm text-ink-2">
            Target role
            <select value={role} onChange={(e) => update({ role: e.target.value })} disabled={refreshing}
              className="focus-ring min-w-0 max-w-full rounded-xl border border-line bg-card-2 px-3 py-2 text-sm text-ink">
              {(roles.length ? roles : [a.role]).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </label>
          <ModeToggle mode={mode} onChange={(m) => update({ mode: m })} busy={refreshing} />
        </div>
      </header>

      <ParseQualityBanner quality={a.parse_quality} />

      <div className={`grid grid-cols-1 gap-6 transition-opacity lg:grid-cols-12 [&>*]:min-w-0 ${refreshing ? 'opacity-60' : ''}`} aria-busy={refreshing}>
        <Card title="Overall score" subtitle="Deterministic and rule-based" className="animate-rise lg:col-span-3">
          <div className="flex flex-col items-center gap-4">
            <ScoreRing value={a.score.total} label="Resume score" hero statusText={a.score.band} />
            <p className="text-center text-sm text-ink-2">
              {a.feedback.total === 0 ? 'No issues found.' : `${a.feedback.total} ${a.feedback.total === 1 ? 'suggestion' : 'suggestions'}, ${high} high priority.`}
            </p>
          </div>
        </Card>
        <Card title="Score by parameter" subtitle="Share of each parameter's points earned. Hover for raw points."
          className="animate-rise lg:col-span-4">
          <SubScoreChart parameters={a.score.parameters} />
        </Card>
        <div className="animate-rise lg:col-span-5"><AtsPanel ats={a.ats} /></div>
      </div>

      {mode === 'ai' && <AiFeedbackPanel analysis={refreshing ? null : a} loading={refreshing} />}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 [&>*]:min-w-0">
        <div className="lg:col-span-7"><SuggestionList feedback={a.feedback} /></div>
        <div className="lg:col-span-5"><ScoreBreakdown parameters={a.score.parameters} /></div>
      </div>
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6" aria-busy="true" aria-label="Loading analysis">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Skeleton className="h-80 lg:col-span-3" /><Skeleton className="h-80 lg:col-span-4" /><Skeleton className="h-80 lg:col-span-5" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12"><Skeleton className="h-96 lg:col-span-7" /><Skeleton className="h-96 lg:col-span-5" /></div>
    </div>
  )
}
