// Horizontal bar chart of the six scoring parameters as % of their maximum.
// Single series -> one hue; value labels at the bar ends; hover tooltip with raw points.
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useThemeContext } from '../hooks/themeContext.js'
import { useTokens } from '../hooks/useTheme.js'

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <div className="rounded-lg border border-line bg-card px-3 py-2 text-sm shadow-lg">
      <p className="font-medium text-ink">{row.label}</p>
      <p className="text-ink-2 tabular-nums">{row.score} / {row.max} points ({row.percent}%)</p>
    </div>
  )
}

const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

export default function SubScoreChart({ parameters }) {
  const { theme } = useThemeContext()
  const t = useTokens(theme, ['accent', 'grid', 'ink-2', 'ink-3', 'card-2'])
  const data = Object.values(parameters).map((p) => ({
    label: p.label, score: p.score, max: p.max, percent: Math.round((p.score / p.max) * 100),
  }))

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 48, bottom: 4, left: 4 }} barCategoryGap="28%">
          <CartesianGrid horizontal={false} stroke={t.grid} strokeWidth={1} />
          <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v) => `${v}%`}
            tick={{ fill: t['ink-3'], fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="label" width={112} tick={{ fill: t['ink-2'], fontSize: 12 }}
            axisLine={false} tickLine={false} />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: t['card-2'] }} />
          <Bar dataKey="percent" fill={t.accent} radius={[0, 4, 4, 0]} maxBarSize={20} isAnimationActive={!reduceMotion()}>
            <LabelList dataKey="percent" position="right" formatter={(v) => `${v}%`}
              style={{ fill: t['ink-2'], fontSize: 12, fontWeight: 500 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
