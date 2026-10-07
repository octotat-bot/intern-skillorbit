import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="mx-auto max-w-xl px-4 py-32 text-center">
      <p className="font-serif text-7xl italic text-ink-3">404</p>
      <h1 className="mt-4 text-xl font-medium text-ink">This page doesn't exist</h1>
      <Link to="/" className="btn-primary mt-8">Analyze a resume</Link>
    </div>
  )
}
