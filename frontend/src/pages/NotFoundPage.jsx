import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="text-sm font-medium text-accent-ink">404</p>
      <h1 className="mt-2 text-2xl font-semibold text-ink">Page not found</h1>
      <Link to="/" className="btn-primary mt-6">Analyze a resume</Link>
    </div>
  )
}
