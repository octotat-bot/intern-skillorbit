// Minimal Recharts bar list: share of each parameter's points earned.
// One series in one hue, quiet track behind each bar, values printed at the right,
// hover tooltip with the raw points.
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useThemeContext } from '../hooks/themeContext.js'
import { prefersReducedMotion } from '../hooks/useCountUp.js'
import { useTokens } from '../hooks/useTheme.js'

const ROW_HEIGHT = 38
const LABEL_WIDTH = 92
const VALUE_WIDTH = 64
// Short axis labels; the full parameter name appears in the tooltip.
const SHORT_LABELS = {
  contact: 'Contact', structure: 'Structure', skills: 'Skills',
  projects: 'Projects', education: 'Education', quality: 'Writing',
}

/** Left-aligned category label (Recharts right-aligns axis ticks by default). */
function LabelTick({ y, payload, fill }) {
  return (
    <text x={0} y={y} dy={4} textAnchor="start" fill={fill} fontSize={13}>{payload.value}</text>
  )
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <div className="rounded-xl border border-line bg-surface px-3 py-2 text-xs shadow-xl shadow-black/20">
      <p className="font-medium text-ink">{row.label}</p>
      <p className="mt-0.5 tabular-nums text-ink-2">{row.score} of {row.max} points · {row.percent}%</p>
    </div>
  )
}

export default function SubScoreChart({ parameters }) {
  const { theme } = useThemeContext()
  const t = useTokens(theme, ['accent', 'track', 'ink-2', 'ink'])
  const data = Object.entries(parameters).map(([key, p]) => ({
    short: SHORT_LABELS[key] || p.label,
    label: p.label,
    score: p.score,
    max: p.max,
    percent: Math.round((p.score / p.max) * 100),
    value: `${p.score}/${p.max}`,
  }))

  return (
    <div style={{ height: data.length * ROW_HEIGHT }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barCategoryGap={15}>
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis yAxisId="label" type="category" dataKey="short" width={LABEL_WIDTH} axisLine={false} tickLine={false}
            tick={<LabelTick fill={t['ink-2']} />} />
          <YAxis yAxisId="value" type="category" dataKey="value" orientation="right" width={VALUE_WIDTH} axisLine={false}
            tickLine={false} tick={{ fill: t.ink, fontSize: 13, textAnchor: 'end', dx: VALUE_WIDTH - 8 }} />
          <Tooltip content={<ChartTooltip />} cursor={false} />
          <Bar yAxisId="label" dataKey="percent" fill={t.accent} barSize={6} radius={[3, 3, 3, 3]}
            background={{ fill: t.track, radius: 3 }} isAnimationActive={!prefersReducedMotion()} animationDuration={900} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
