import { Suspense, lazy } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import Icon from './components/Icon.jsx'
import { ThemeContext } from './hooks/themeContext.js'
import { useTheme } from './hooks/useTheme.js'
import NotFoundPage from './pages/NotFoundPage.jsx'
import UploadPage from './pages/UploadPage.jsx'

// The dashboard pulls in Recharts; load it only when needed.
const DashboardPage = lazy(() => import('./pages/DashboardPage.jsx'))

/** Brand mark: a partial ring, echoing the score meter. */
function Mark() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity=".25" strokeWidth="2.5" />
      <path d="M12 3a9 9 0 0 1 8.6 11.7" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  )
}

export default function App() {
  const theme = useTheme()
  return (
    <ThemeContext.Provider value={theme}>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-page">
        Skip to content
      </a>
      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-40 border-b border-line/60 bg-page/70 backdrop-blur-xl">
          <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-8">
            <Link to="/" className="focus-ring flex items-center gap-2.5 rounded-full text-[15px] font-medium tracking-tight text-ink">
              <Mark />
              Resume Analyzer
            </Link>
            <button type="button" onClick={theme.toggle} className="btn-ghost !size-9 !px-0"
              aria-label={`Switch to ${theme.theme === 'dark' ? 'light' : 'dark'} mode`}>
              <Icon name={theme.theme === 'dark' ? 'sun' : 'moon'} className="size-4" />
            </button>
          </div>
        </header>
        <main id="main" className="flex-1">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/analysis/:resumeId" element={
              <Suspense fallback={<p className="p-16 text-center text-sm text-ink-3">Loading...</p>}><DashboardPage /></Suspense>
            } />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
        <footer className="mx-auto w-full max-w-6xl px-4 py-10 text-xs text-ink-3 sm:px-8">
          Deterministic, explainable scoring. The ATS score is a heuristic, not a vendor-verified metric.
        </footer>
      </div>
    </ThemeContext.Provider>
  )
}
