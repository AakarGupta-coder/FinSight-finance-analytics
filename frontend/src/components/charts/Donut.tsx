import type { ReactNode } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useAppData } from '../../lib/appData'
import { dataSignature, useChartAnimation } from '../../lib/motion'
import { TooltipBox, type TooltipArgs } from './Charts'

export interface DonutSegment {
  key: string
  label: string
  value: number
  color: string
}

/**
 * Donut with a centred label. Segments must sum to the figure shown in the
 * centre (callers pass real totals; nothing is normalised or invented here).
 * A 2px surface-coloured stroke separates adjacent segments.
 */
export function Donut({ segments, center, caption, size = 176, ariaLabel }: {
  segments: DonutSegment[]; center: ReactNode; caption?: ReactNode; size?: number; ariaLabel: string
}) {
  const { money } = useAppData()
  const total = segments.reduce((s, x) => s + x.value, 0)
  const animate = useChartAnimation(dataSignature(segments.map((s) => s.value)))
  return (
    <div className="relative mx-auto" style={{ width: size, height: size }} role="img" aria-label={ariaLabel}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie isAnimationActive={animate} animationDuration={700} animationEasing="ease-out" data={segments} dataKey="value" nameKey="label" innerRadius="70%" outerRadius="100%"
            startAngle={90} endAngle={-270} stroke="var(--surface)" strokeWidth={2} paddingAngle={0}>
            {segments.map((s) => <Cell key={s.key} fill={s.color} />)}
          </Pie>
          <Tooltip content={(p: TooltipArgs) => {
            if (!p.active || !p.payload?.length) return null
            const seg = p.payload[0].payload as DonutSegment
            const share = total ? Math.round((seg.value / total) * 1000) / 10 : 0
            return <TooltipBox title={seg.label} rows={[{ label: 'Amount', value: money(seg.value), color: seg.color }, { label: 'Share', value: `${share}%` }]} />
          }} />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-[17px] font-semibold leading-tight tracking-tight tabular text-text">{center}</span>
        {caption && <span className="mt-0.5 max-w-[60%] text-[11px] leading-tight text-muted">{caption}</span>}
      </div>
    </div>
  )
}

/** Compact legend: swatch · label · amount · share. Text carries identity, not colour alone. */
export function DonutLegend({ rows }: { rows: { key: string; label: string; color: string; value: string; detail?: string }[] }) {
  return (
    <ul className="min-w-0 space-y-2" aria-label="Legend">
      {rows.map((r) => (
        <li key={r.key} className="flex items-center gap-2 text-[12.5px]">
          <span className="h-2.5 w-2.5 shrink-0 rounded-[3px]" style={{ background: r.color }} aria-hidden />
          <span className="min-w-0 flex-1 truncate text-text-2">{r.label}</span>
          <span className="shrink-0 font-medium tabular text-text">{r.value}</span>
          {r.detail && <span className="w-10 shrink-0 text-right tabular text-muted">{r.detail}</span>}
        </li>
      ))}
    </ul>
  )
}
