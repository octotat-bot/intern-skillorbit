// Small inline SVG icon set (no icon library dependency). Decorative by default.
const PATHS = {
  upload: 'M12 16V4m0 0l-4 4m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2',
  file: 'M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5zm0 0v5h5',
  check: 'M5 13l4 4L19 7',
  alert: 'M12 9v4m0 4h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z',
  info: 'M12 16v-4m0-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  x: 'M6 18L18 6M6 6l12 12',
  chevron: 'M19 9l-7 7-7-7',
  sparkles: 'M5 3v4M3 5h4M6 17v4m-2-2h4M13 3l2.3 6.9L22 12l-6.7 2.1L13 21l-2.3-6.9L4 12l6.7-2.1L13 3z',
  sun: 'M12 3v2m0 14v2m9-9h-2M5 12H3m15.4-6.4l-1.4 1.4M7 17l-1.4 1.4m12.8 0L17 17M7 7L5.6 5.6M16 12a4 4 0 11-8 0 4 4 0 018 0z',
  moon: 'M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z',
  arrowLeft: 'M10 19l-7-7m0 0l7-7m-7 7h18',
  refresh: 'M4 4v5h5M20 20v-5h-5M5.6 15A7 7 0 0018.4 15M18.4 9A7 7 0 005.6 9',
  book: 'M12 6.3C10.8 5.5 9.2 5 7.5 5S4.2 5.5 3 6.3v13C4.2 18.5 5.8 18 7.5 18s3.3.5 4.5 1.3m0-13C13.2 5.5 14.8 5 16.5 5s3.3.5 4.5 1.3v13c-1.2-.8-2.8-1.3-4.5-1.3s-3.3.5-4.5 1.3m0-13v13',
  arrowRight: 'M14 5l7 7m0 0l-7 7m7-7H3',
}

export default function Icon({ name, className = 'size-5', title }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" className={className} aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}>
      {title && <title>{title}</title>}
      <path d={PATHS[name]} />
    </svg>
  )
}
