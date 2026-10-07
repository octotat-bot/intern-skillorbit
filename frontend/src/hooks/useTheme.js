import { useCallback, useEffect, useState } from 'react'

/** Dark-first theme stored in localStorage (wrapped: storage may be blocked). */
export function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || 'dark')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('theme', theme) } catch { /* ignore */ }
  }, [theme])

  const toggle = useCallback(() => setTheme((t) => (t === 'dark' ? 'light' : 'dark')), [])
  return { theme, toggle }
}

/** Resolved CSS token values for SVG/Recharts props, re-read when the theme changes. */
export function useTokens(theme, names) {
  const [values, setValues] = useState({})
  const key = names.join(',')
  useEffect(() => {
    const styles = getComputedStyle(document.documentElement)
    setValues(Object.fromEntries(key.split(',').map((n) => [n, styles.getPropertyValue(`--${n}`).trim()])))
  }, [theme, key])
  return values
}
