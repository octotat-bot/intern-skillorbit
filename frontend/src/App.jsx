import { Suspense, lazy } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import Icon from './components/Icon.jsx'
import { ThemeContext } from './hooks/themeContext.js'
import { useTheme } from './hooks/useTheme.js'
import NotFoundPage from './pages/NotFoundPage.jsx'
import UploadPage from './pages/UploadPage.jsx'

// The dashboard pulls in Recharts; load it only when needed.
const DashboardPage = lazy(() => import('./pages/DashboardPage.jsx'))

export default function App() {
  const theme = useTheme()
  return (
    <ThemeContext.Provider value={theme}>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-card focus:px-3 focus:py-2">
        Skip to content
      </a>
      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-40 border-b border-line bg-page/80 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
            <Link to="/" className="focus-ring flex items-center gap-2 rounded-lg font-semibold text-ink">
              <img src="/favicon.svg" alt="" className="size-7" />
              Smart Resume Analyzer
            </Link>
            <button type="button" onClick={theme.toggle} className="btn-secondary !px-2.5"
              aria-label={`Switch to ${theme.theme === 'dark' ? 'light' : 'dark'} mode`}>
              <Icon name={theme.theme === 'dark' ? 'sun' : 'moon'} className="size-4" />
            </button>
          </div>
        </header>
        <main id="main" className="flex-1">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/analysis/:resumeId" element={<Suspense fallback={<p className="p-8 text-center text-ink-3">Loading dashboard...</p>}><DashboardPage /></Suspense>} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
        <footer className="border-t border-line py-6 text-center text-xs text-ink-3">
          Scores are deterministic and explainable. The ATS score is a heuristic, not a vendor-verified metric.
        </footer>
      </div>
    </ThemeContext.Provider>
  )
}
