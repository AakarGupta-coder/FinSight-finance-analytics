import { useId } from 'react'
import { Area, AreaChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAppData } from '../../lib/appData'
import { dataSignature, useChartAnimation } from '../../lib/motion'
import { axisProps, TooltipBox, type TooltipArgs } from './Charts'

export interface TrendPoint {
  key: string
  label: string
  /** Tooltip heading, e.g. a full date. */
  title: string
  value: number
  /** Optional reference series (e.g. the monthly budget that applied). */
  reference?: number | null
}

/**
 * The dashboard's primary chart: one emerald area series with a restrained fill,
 * plus an optional dashed reference line. A legend is shown only when the
 * reference series is present (two series on screen).
 */
export function TrendArea({ data, height = 280, valueLabel, referenceLabel }: {
  data: TrendPoint[]; height?: number; valueLabel: string; referenceLabel?: string
}) {
  const { money } = useAppData()
  const gid = useId().replace(/:/g, '')
  const hasReference = !!referenceLabel && data.some((d) => d.reference != null)
  // Draw in on entry and when the figures change (e.g. another month), not on unrelated re-renders.
  const animate = useChartAnimation(dataSignature(data.flatMap((d) => [d.value, d.reference])))
  return (
    <div>
      {hasReference && (
        <ul className="mb-2 flex flex-wrap justify-end gap-4 text-xs text-text-2" aria-label="Legend">
          <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: 'var(--series-single)' }} />{valueLabel}</li>
          <li className="flex items-center gap-1.5"><span className="h-0 w-4 border-t-2 border-dashed" style={{ borderColor: 'var(--series-reference)' }} />{referenceLabel}</li>
        </ul>
      )}
      <div style={{ height }} role="img" aria-label={`${valueLabel} trend chart`}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={`trend-${gid}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--series-single)" stopOpacity={0.28} />
                <stop offset="100%" stopColor="var(--series-single)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeDasharray="4 6" />
            <XAxis dataKey="label" {...axisProps} interval="preserveStartEnd" minTickGap={28} />
            <YAxis {...axisProps} width={58} tickFormatter={(v: number) => money(v, { compact: true })} />
            <Tooltip
              cursor={{ stroke: 'var(--chart-cursor)', strokeDasharray: '4 4', strokeWidth: 1.5 }}
              content={(p: TooltipArgs) => {
                if (!p.active || !p.payload?.length) return null
                const row = p.payload[0].payload as TrendPoint
                const rows = [{ label: valueLabel, value: money(row.value), color: 'var(--series-single)' }]
                if (hasReference && row.reference != null) rows.push({ label: referenceLabel!, value: money(row.reference), color: 'var(--series-reference)' })
                return <TooltipBox title={row.title} rows={rows} />
              }}
            />
            <Area isAnimationActive={animate} animationDuration={750} animationEasing="ease-out" type="monotone" dataKey="value" stroke="var(--series-single)" strokeWidth={2}
              fill={`url(#trend-${gid})`} activeDot={{ r: 5, strokeWidth: 3, stroke: 'var(--surface)', fill: 'var(--series-single)' }} dot={false} />
            {hasReference && (
              <Line isAnimationActive={animate} animationDuration={750} animationEasing="ease-out" type="stepAfter" dataKey="reference" stroke="var(--series-reference)" strokeWidth={1.5}
                strokeDasharray="5 4" dot={false} activeDot={false} connectNulls={false} />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
