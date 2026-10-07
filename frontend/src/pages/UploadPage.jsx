import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Dropzone from '../components/Dropzone.jsx'
import Icon from '../components/Icon.jsx'
import RoleSelector from '../components/RoleSelector.jsx'
import { ErrorState, Skeleton } from '../components/ui.jsx'
import { errorMessage, fetchRoles, uploadResume } from '../api/client.js'

const FEATURES = [
  { figure: '/100', title: 'Explainable score', text: 'Six weighted parameters with the evidence behind every point.' },
  { figure: 'ATS', title: 'Keyword match', text: 'Must-have skills for your role, plus layout risks.' },
  { figure: '40', title: 'Rules', text: 'Prioritized fixes, with optional AI rewrites that cite sources.' },
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
      navigate(`/analysis/${receipt.resume_id}?role=${role}`)
    } catch (err) {
      setPhase('error'); setError(errorMessage(err))
    }
  }

  const busy = phase === 'uploading'
  return (
    <div className="mx-auto max-w-4xl px-4 pb-16 pt-16 sm:px-8 sm:pt-24">
      <header className="animate-rise text-center">
        <p className="eyebrow">Resume analyzer for students</p>
        <h1 className="mx-auto mt-5 max-w-3xl text-[40px] font-medium leading-[1.05] tracking-[-0.035em] text-ink sm:text-6xl">
          Know exactly where your resume <span className="font-serif text-[1.08em] font-normal italic tracking-[-0.01em]">stands.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-ink-2 sm:text-lg">
          A score out of 100, an ATS keyword match and a prioritized list of fixes,
          each backed by the evidence that produced it.
        </p>
      </header>

      <form onSubmit={submit} className="animate-rise mt-16 space-y-12 [animation-delay:120ms]" aria-busy={busy}>
        {rolesError ? (
          <ErrorState title="Couldn't load roles" message={rolesError} onRetry={loadRoles} />
        ) : roles ? (
          <RoleSelector roles={roles} value={role} onChange={setRole} disabled={busy} />
        ) : (
          <div aria-label="Loading roles">
            <Skeleton className="mb-4 h-3 w-28" />
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-[74px] !rounded-2xl" />)}
            </div>
          </div>
        )}

        <Dropzone file={file} disabled={busy}
          onFile={(f) => { setFile(f); setError(null); setPhase('idle') }}
          onReject={(message) => { setFile(null); setError(message); setPhase('error') }} />

        <div className="flex flex-col items-center gap-4">
          <button type="submit" className="btn-primary w-full sm:w-auto sm:min-w-56" disabled={!file || !role || busy}>
            {busy ? (progress < 100 ? `Uploading ${progress}%` : 'Analyzing...') : 'Analyze resume'}
            {!busy && <Icon name="arrowRight" className="size-4" />}
          </button>
          <div aria-live="polite" className="w-full max-w-sm">
            {busy && (
              <div className="h-px overflow-hidden bg-line" role="progressbar" aria-label="Upload progress"
                aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
                <div className="h-full bg-ink transition-[width] duration-300" style={{ width: `${progress}%` }} />
              </div>
            )}
            {phase === 'error' && error && (
              <p role="alert" className="flex items-center justify-center gap-2 text-sm text-critical-ink">
                <Icon name="alert" className="size-4" /> {error}
              </p>
            )}
          </div>
          <p className="text-xs text-ink-3">Parsed in memory. Your file is never stored.</p>
        </div>
      </form>

      <ul className="mt-24 grid gap-px overflow-hidden rounded-3xl border border-line bg-line sm:grid-cols-3">
        {FEATURES.map((f) => (
          <li key={f.title} className="bg-page p-6">
            <p className="font-serif text-3xl italic text-ink">{f.figure}</p>
            <p className="mt-4 text-sm font-medium text-ink">{f.title}</p>
            <p className="mt-1 text-sm leading-relaxed text-ink-3">{f.text}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
