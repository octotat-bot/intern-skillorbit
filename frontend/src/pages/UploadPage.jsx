import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Dropzone from '../components/Dropzone.jsx'
import Icon from '../components/Icon.jsx'
import RoleSelector from '../components/RoleSelector.jsx'
import { ErrorState, Skeleton } from '../components/ui.jsx'
import { errorMessage, fetchRoles, uploadResume } from '../api/client.js'

const FEATURES = [
  { title: 'Explainable /100 score', text: 'Six weighted parameters, each with the evidence behind every point.' },
  { title: 'ATS keyword match', text: 'Must-have and nice-to-have skills for your target role, plus layout risks.' },
  { title: 'Prioritized fixes', text: '40 deterministic rules, with optional AI rewrites grounded in cited guidance.' },
]

export default function UploadPage() {
  const navigate = useNavigate()
  const [roles, setRoles] = useState(null)
  const [rolesError, setRolesError] = useState(null)
  const [role, setRole] = useState('')
  const [file, setFile] = useState(null)
  const [phase, setPhase] = useState('idle') // idle | uploading | error
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)

  const loadRoles = () => {
    setRolesError(null)
    fetchRoles()
      .then((list) => { setRoles(list); setRole((current) => current || list[0]?.id || '') })
      .catch((err) => setRolesError(errorMessage(err)))
  }
  useEffect(loadRoles, [])

  const submit = async (event) => {
    event.preventDefault()
    if (!file || !role) return
    setPhase('uploading'); setProgress(0); setError(null)
    try {
      const receipt = await uploadResume(file, setProgress)
      navigate(`/analysis/${receipt.resume_id}?role=${role}`, { state: { receipt } })
    } catch (err) {
      setPhase('error'); setError(errorMessage(err))
    }
  }

  const busy = phase === 'uploading'
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-14">
      <div className="animate-rise text-center">
        <p className="text-sm font-medium text-accent-ink">AI resume analyzer for students</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">See your resume the way a recruiter and an ATS do</h1>
        <p className="mx-auto mt-3 max-w-2xl text-ink-2">
          Upload a resume and pick a role. You get a score out of 100, an ATS keyword match, missing skills and a prioritized fix list. Every result shows the evidence that produced it.
        </p>
      </div>

      <form onSubmit={submit} className="mt-10 space-y-8 rounded-3xl border border-line bg-card/60 p-5 sm:p-8" aria-busy={busy}>
        {rolesError ? (
          <ErrorState title="Couldn't load roles" message={rolesError} onRetry={loadRoles} />
        ) : roles ? (
          <RoleSelector roles={roles} value={role} onChange={setRole} disabled={busy} />
        ) : (
          <div className="grid gap-2 sm:grid-cols-3" aria-label="Loading roles">
            {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-20" />)}
          </div>
        )}

        <Dropzone file={file} disabled={busy}
          onFile={(f) => { setFile(f); setError(null); setPhase('idle') }}
          onReject={(message) => { setFile(null); setError(message); setPhase('error') }} />

        <div aria-live="polite">
          {busy && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-ink-2">{progress < 100 ? 'Uploading...' : 'Parsing and checking layout...'}</span>
                <span className="tabular-nums text-ink-3">{progress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-accent/20" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} aria-label="Upload progress">
                <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}
          {phase === 'error' && error && <ErrorState title="Upload failed" message={error} />}
        </div>

        <div className="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-ink-3">Your file is parsed in memory and not stored; only the extracted text is kept.</p>
          <button type="submit" className="btn-primary" disabled={!file || !role || busy}>
            {busy ? 'Analyzing...' : 'Analyze resume'} <Icon name="arrowRight" className="size-4" />
          </button>
        </div>
      </form>

      <ul className="mt-10 grid gap-4 sm:grid-cols-3">
        {FEATURES.map((f) => (
          <li key={f.title} className="rounded-2xl border border-line bg-card p-5">
            <p className="font-medium text-ink">{f.title}</p>
            <p className="mt-1 text-sm text-ink-2">{f.text}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
