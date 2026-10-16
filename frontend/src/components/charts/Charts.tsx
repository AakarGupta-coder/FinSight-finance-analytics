import { useEffect, useMemo, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

// Minimal shape of the props Recharts passes to custom tooltip content.
export interface TooltipArgs { active?: boolean; payload?: readonly { value?: unknown; payload?: any }[] }
import { useAppData } from '../../lib/appData'
import { formatDate } from '../../lib/format'
import { categoryColor, cn, hasOwnSlot } from '../../lib/utils'
import type { CategoryRow, DailyPoint, MonthlyPoint } from '../../lib/types'
import { dataSignature, useChartAnimation } from '../../lib/motion'

// Shared chart conventions: thin marks, 4px rounded data ends, recessive grid,
// one y-axis, hover tooltip on every mark, text in ink tokens (never series colors).

export const axisProps = { stroke: 'var(--chart-axis)', tickLine: false, axisLine: false, fontSize: 12 } as const

export function TooltipBox({ title, rows }: { title: string; rows: { label: string; value: string; color?: string }[] }) {
  return (
    // Glass tooltip: floats over the chart; values stay high-contrast and tabular.
    <div className="glass-strong min-w-[140px] rounded-lg border px-3 py-2 text-xs shadow-float">
      <p className="mb-1 font-semibold text-text">{title}</p>
      {rows.map((r) => (
        <div key={r.label} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-muted">
            {r.color && <span className="inline-block h-2 w-2 rounded-sm" style={{ background: r.color }} />}{r.label}
          </span>
          <span className="font-medium tabular text-text">{r.value}</span>
        </div>
      ))}
    </div>
  )
}

/** Bar that grows from empty on first render and glides to new lengths on updates. */
function GrowBar({ pct }: { pct: number }) {
  const [shown, setShown] = useState(0)
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(pct))
    return () => cancelAnimationFrame(id)
  }, [pct])
  return <div className="h-1.5 rounded-full transition-[width] duration-700 ease-[var(--ease-out)]" style={{ width: `${shown}%`, background: 'var(--series-single)' }} />
}

/** Horizontal bars, one hue: category identity comes from the label, magnitude from length. */
export function CategoryBars({ rows, limit = 8, onSelect }: { rows: CategoryRow[]; limit?: number; onSelect?: (category: string) => void }) {
  const { money } = useAppData()
  const shown = rows.slice(0, limit)
  const rest = rows.slice(limit)
  const max = Math.max(...rows.map((r) => r.amount_minor), 1)
  const list = rest.length
    ? [...shown, { category: '__rest', category_name: `${rest.length} more`, amount_minor: rest.reduce((s, r) => s + r.amount_minor, 0),
        share_pct: Math.round(rest.reduce((s, r) => s + (r.share_pct ?? 0), 0) * 10) / 10, count: rest.reduce((s, r) => s + r.count, 0) }]
    : shown
  return (
    <ul className="space-y-2.5" aria-label="Spending by category">
      {list.map((r) => {
        const clickable = onSelect && r.category !== '__rest'
        const content = (
          <>
            <div className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="truncate font-medium text-text">{r.category_name}</span>
              <span className="shrink-0 tabular text-text">{money(r.amount_minor)} <span className="text-muted">· {r.share_pct ?? 0}%</span></span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-[var(--track)]">
              <GrowBar pct={(r.amount_minor / max) * 100} />
            </div>
          </>
        )
        return (
          <li key={r.category} title={`${r.count} transaction(s)`}>
            {clickable ? <button type="button" onClick={() => onSelect!(r.category)} className="block w-full rounded-lg text-left hover:opacity-80">{content}</button> : content}
          </li>
        )
      })}
    </ul>
  )
}

export function DailyBars({ data, height = 220, averageMinor }: { data: DailyPoint[]; height?: number; averageMinor?: number }) {
  const { money } = useAppData()
  const chartData = useMemo(() => data.map((d) => ({ ...d, label: formatDate(d.date, { year: false }) })), [data])
  const animate = useChartAnimation(dataSignature(data.map((d) => d.amount_minor)))
  return (
    <div style={{ height }} role="img" aria-label="Daily spending bar chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 4, left: 0, bottom: 0 }} barCategoryGap={2}>
          <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeDasharray="4 6" />
          <XAxis dataKey="label" {...axisProps} interval="preserveStartEnd" minTickGap={24} />
          <YAxis {...axisProps} width={56} tickFormatter={(v: number) => money(v, { compact: true })} />
          {averageMinor ? <ReferenceLine y={averageMinor} stroke="var(--chart-axis)" strokeDasharray="4 4" /> : null}
          <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.6 }} content={(p: TooltipArgs) =>
            p.active && p.payload?.length ? <TooltipBox title={formatDate(p.payload[0].payload.date)} rows={[{ label: 'Spent', value: money(p.payload[0].value as number) }]} /> : null} />
          <Bar isAnimationActive={animate} animationDuration={650} animationEasing="ease-out" dataKey="amount_minor" fill="var(--series-single)" radius={[3, 3, 0, 0]} maxBarSize={18} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Monthly totals, optionally stacked by the top categories (fixed colors per category, rest folded into Other). */
export function MonthlyBars({ data, stacked = false, height = 240, budgetMinor, categoryNames }: {
  data: MonthlyPoint[]; stacked?: boolean; height?: number; budgetMinor?: number | null; categoryNames?: Record<string, string>
}) {
  const { money, categoryName } = useAppData()
  const name = (c: string) => (c === 'other_folded' ? 'Other' : categoryNames?.[c] ?? categoryName(c))
  const { rows, keys } = useMemo(() => {
    if (!stacked) return { rows: data.map((d) => ({ label: d.label, month: d.month, total: d.total_minor }) as Record<string, number | string>), keys: [] as string[] }
    const totals: Record<string, number> = {}
    data.forEach((d) => Object.entries(d.by_category).forEach(([k, v]) => { totals[k] = (totals[k] ?? 0) + v }))
    const top = Object.entries(totals).filter(([k]) => hasOwnSlot(k)).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([k]) => k)
    const rows = data.map((d) => {
      const row: Record<string, number | string> = { label: d.label, month: d.month, total: d.total_minor }
      let other = 0
      Object.entries(d.by_category).forEach(([k, v]) => { if (top.includes(k)) row[k] = v; else other += v })
      row.other_folded = other
      return row
    })
    return { rows, keys: [...top, 'other_folded'] }
  }, [data, stacked])
  const animate = useChartAnimation(dataSignature(data.map((d) => d.total_minor)) + (stacked ? 's' : ''))

  return (
    <div>
      <div style={{ height }} role="img" aria-label="Monthly spending bar chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 4, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeDasharray="4 6" />
            <XAxis dataKey="label" {...axisProps} />
            <YAxis {...axisProps} width={56} tickFormatter={(v: number) => money(v, { compact: true })} />
            {budgetMinor ? <ReferenceLine y={budgetMinor} stroke="var(--danger)" strokeDasharray="4 4"
              label={{ value: 'Budget', position: 'insideTopRight', fill: 'var(--danger)', fontSize: 11 }} /> : null}
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.6 }} content={(p: TooltipArgs) => {
              if (!p.active || !p.payload?.length) return null
              const row = p.payload[0].payload as Record<string, number | string>
              const items = stacked
                ? keys.filter((k) => Number(row[k] ?? 0) > 0).map((k) => ({ label: name(k), value: money(Number(row[k])), color: k === 'other_folded' ? 'var(--series-other)' : categoryColor(k) }))
                : []
              return <TooltipBox title={String(row.label)} rows={[...items, { label: 'Total', value: money(Number(row.total)) }]} />
            }} />
            {stacked
              ? keys.map((k, i) => (
                <Bar isAnimationActive={animate} animationDuration={650} animationEasing="ease-out" key={k} dataKey={k} stackId="a" fill={k === 'other_folded' ? 'var(--series-other)' : categoryColor(k)} maxBarSize={36}
                  stroke="var(--surface)" strokeWidth={1} radius={i === keys.length - 1 ? [4, 4, 0, 0] : 0} />
              ))
              : <Bar isAnimationActive={animate} animationDuration={650} animationEasing="ease-out" dataKey="total" maxBarSize={36} radius={[4, 4, 0, 0]}>
                {rows.map((r, i) => <Cell key={i} fill={budgetMinor && Number(r.total) > budgetMinor ? 'var(--danger)' : 'var(--series-single)'} />)}
              </Bar>}
          </BarChart>
        </ResponsiveContainer>
      </div>
      {stacked && keys.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-text-2" aria-label="Legend">
          {keys.map((k) => (
            <li key={k} className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: k === 'other_folded' ? 'var(--series-other)' : categoryColor(k) }} />{name(k)}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Simple accessible data table toggle for charts. */
export function ChartTableToggle({ chart, table }: { chart: React.ReactNode; table: React.ReactNode }) {
  const [showTable, setShowTable] = useState(false)
  return (
    <div>
      <div className="mb-2 flex justify-end">
        <button type="button" onClick={() => setShowTable((s) => !s)} className={cn('text-xs font-medium text-accent hover:underline')}>
          {showTable ? 'Show chart' : 'Show table'}
        </button>
      </div>
      {showTable ? table : chart}
    </div>
  )
}
