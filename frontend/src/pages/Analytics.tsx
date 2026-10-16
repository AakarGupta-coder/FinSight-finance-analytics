import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { CalendarRange, CreditCard, ReceiptText, Store, TrendingUp } from 'lucide-react'
import { useAppData } from '../lib/appData'
import { addDays, formatDate, monthStart, shiftMonth } from '../lib/format'
import { useApi, useDocumentTitle } from '../lib/hooks'
import type { RangeAnalytics } from '../lib/types'
import { categoryColor, hasOwnSlot } from '../lib/utils'
import { Card, CardBody, CardHeader, EmptyState, ErrorState, Input, PageHeader, Segmented, Skeleton, StatCard } from '../components/ui/primitives'
import { CategoryBars, ChartTableToggle, MonthlyBars } from '../components/charts/Charts'
import { TrendArea } from '../components/charts/Trend'
import { Donut, DonutLegend, type DonutSegment } from '../components/charts/Donut'

type Preset = '30d' | 'month' | '3m' | '6m' | '12m' | 'custom'

export default function AnalyticsPage() {
  useDocumentTitle('Analytics')
  const { today, money } = useAppData()
  const navigate = useNavigate()
  const [preset, setPreset] = useState<Preset>('3m')
  const [custom, setCustom] = useState({ start: addDays(today, -29), end: today })

  const range = useMemo(() => {
    switch (preset) {
      case '30d': return { start: addDays(today, -29), end: today }
      case 'month': return { start: monthStart(today), end: today }
      case '3m': return { start: `${shiftMonth(today.slice(0, 7), -2)}-01`, end: today }
      case '6m': return { start: `${shiftMonth(today.slice(0, 7), -5)}-01`, end: today }
      case '12m': return { start: `${shiftMonth(today.slice(0, 7), -11)}-01`, end: today }
      default: return custom
    }
  }, [preset, custom, today])
  const valid = range.start <= range.end
  const { data, error, reload } = useApi<RangeAnalytics>(valid ? '/analytics' : null, range)

  // Category donut: real totals for the range; categories without a fixed colour fold into "Other".
  const donut = useMemo(() => {
    const rows = data?.categories ?? []
    const named = rows.filter((r) => hasOwnSlot(r.category)).slice(0, 6)
    const rest = rows.filter((r) => !named.includes(r))
    const segs: DonutSegment[] = named.map((r) => ({ key: r.category, label: r.category_name, value: r.amount_minor, color: categoryColor(r.category) }))
    const restTotal = rest.reduce((a, r) => a + r.amount_minor, 0)
    if (restTotal > 0) segs.push({ key: '__other', label: rest.length === 1 ? rest[0].category_name : `Other (${rest.length})`, value: restTotal, color: 'var(--series-other)' })
    return segs
  }, [data])

  return (
    <>
      <PageHeader title="Analytics" description={`${formatDate(range.start)} – ${formatDate(range.end)}`}
        actions={<Segmented label="Date range" value={preset} onChange={setPreset} size="sm" options={[
          { value: '30d', label: '30 days' }, { value: 'month', label: 'This month' }, { value: '3m', label: '3 months' },
          { value: '6m', label: '6 months' }, { value: '12m', label: '12 months' }, { value: 'custom', label: 'Custom' }]} />} />

      {preset === 'custom' && (
        <Card className="mb-4 flex flex-wrap items-end gap-3 p-4">
          <label className="text-xs font-medium text-muted">From<Input type="date" className="mt-1" value={custom.start} max={custom.end} onChange={(e) => setCustom((c) => ({ ...c, start: e.target.value }))} /></label>
          <label className="text-xs font-medium text-muted">To<Input type="date" className="mt-1" value={custom.end} max={today} onChange={(e) => setCustom((c) => ({ ...c, end: e.target.value }))} /></label>
          {!valid && <p className="text-xs text-danger">Start date must be before end date.</p>}
        </Card>
      )}

      {error ? <Card><ErrorState error={error} onRetry={reload} /></Card> : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard emphasis icon={<ReceiptText className="h-[18px] w-[18px]" />} label="Total spent" loading={!data} value={money(data?.total_minor ?? 0)} sub={data && `${data.days} day(s)`} />
            <StatCard icon={<CalendarRange className="h-[18px] w-[18px]" />} label="Transactions" loading={!data} value={data?.transaction_count ?? 0} />
            <StatCard icon={<TrendingUp className="h-[18px] w-[18px]" />} label="Average per day" loading={!data} value={money(data?.average_daily_minor ?? 0)} />
            <StatCard icon={<CreditCard className="h-[18px] w-[18px]" />} label="Average transaction" loading={!data} value={money(data?.average_transaction_minor ?? 0)} />
          </div>

          {data && data.transaction_count === 0 ? (
            <Card className="mt-4"><EmptyState title="No spending in this period" description="Choose a wider range or add transactions." /></Card>
          ) : (
            <>
              <div className="mt-4 grid gap-4 xl:grid-cols-12">
                <Card className="xl:col-span-8">
                  <CardHeader title="Spending by month" description="Top categories shown individually; the rest are grouped as Other" />
                  <CardBody>
                    {!data ? <Skeleton className="h-64" /> : (
                      <ChartTableToggle
                        chart={<MonthlyBars data={data.monthly} stacked height={280} categoryNames={data.category_names} />}
                        table={<table className="w-full text-[13px]"><thead><tr className="border-b border-border text-left text-xs text-muted"><th className="py-2">Month</th><th className="py-2 text-right">Total</th></tr></thead>
                          <tbody className="divide-y divide-border">{data.monthly.map((m) => <tr key={m.month}><td className="py-1.5">{m.label}</td><td className="py-1.5 text-right tabular">{money(m.total_minor)}</td></tr>)}</tbody></table>} />
                    )}
                  </CardBody>
                </Card>
                <Card className="xl:col-span-4">
                  <CardHeader title="Categories" description="Select a category to see its transactions" />
                  <CardBody className="space-y-5">
                    {!data ? <Skeleton className="h-64" /> : <>
                      <div className="grid items-center gap-4 sm:grid-cols-[150px_1fr] xl:grid-cols-1 2xl:grid-cols-[150px_1fr]">
                        <Donut size={150} segments={donut} center={money(data.total_minor, { compact: true })} caption="Total" ariaLabel={`Category split, total ${money(data.total_minor)}`} />
                        <DonutLegend rows={donut.map((x) => ({ key: x.key, label: x.label, color: x.color, value: `${Math.round((x.value / data.total_minor) * 1000) / 10}%` }))} />
                      </div>
                      <div className="border-t border-border pt-4">
                        <CategoryBars rows={data.categories} limit={8}
                          onSelect={(c) => navigate(`/app/transactions?category=${c}&start=${range.start}&end=${range.end}`)} />
                      </div>
                    </>}
                  </CardBody>
                </Card>
              </div>

              <div className="mt-4 grid items-start gap-4 xl:grid-cols-12">
                <Card className="xl:col-span-8">
                  <CardHeader title="Daily spending" description={data && data.daily.length === 0 ? 'Daily view is available for ranges up to 120 days' : 'Each point is one day'} />
                  <CardBody>
                    {!data ? <Skeleton className="h-56" /> : data.daily.length ? (
                      <TrendArea height={240} valueLabel="Spending"
                        data={data.daily.map((d) => ({ key: d.date, label: formatDate(d.date, { year: false }), title: formatDate(d.date), value: d.amount_minor }))} />
                    ) : <p className="text-[13px] text-muted">Select a shorter range to see daily detail.</p>}
                  </CardBody>
                </Card>
                <div className="space-y-4 xl:col-span-4">
                  <Card>
                    <CardHeader title="Payment methods" />
                    <CardBody>
                      {!data ? <Skeleton className="h-24" /> : (
                        <ul className="space-y-2.5 text-[13px]">
                          {data.payment_methods.map((p) => (
                            <li key={p.payment_method}>
                              <div className="flex justify-between gap-2"><span>{p.name} <span className="text-muted">({p.count})</span></span>
                                <span className="tabular">{money(p.amount_minor)} <span className="text-muted">· {p.share_pct}%</span></span></div>
                              <div className="mt-1 h-1.5 rounded-full bg-[var(--track)]"><div className="h-1.5 rounded-full bg-[var(--series-single)]" style={{ width: `${p.share_pct ?? 0}%` }} /></div>
                            </li>
                          ))}
                        </ul>
                      )}
                    </CardBody>
                  </Card>
                  <Card>
                    <CardHeader title="Top merchants" />
                    <CardBody className="px-0 pb-2">
                      {!data ? <div className="px-5"><Skeleton className="h-24" /></div> : data.top_merchants.length === 0 ? <p className="px-5 text-[13px] text-muted">No merchants recorded.</p> : (
                        <table className="w-full text-[13px]">
                          <tbody className="divide-y divide-border">
                            {data.top_merchants.map((m, i) => (
                              <tr key={m.merchant}>
                                <td className="py-2 pl-5 pr-2"><span className="inline-flex items-center gap-2"><span className="flex h-6 w-6 items-center justify-center rounded-lg bg-surface-2 text-[11px] font-semibold text-muted">{i + 1}</span>
                                  <Store className="h-3.5 w-3.5 text-muted" aria-hidden /><span className="truncate">{m.merchant}</span></span></td>
                                <td className="py-2 text-right text-xs text-muted">{m.count}×</td>
                                <td className="py-2 pl-3 pr-5 text-right font-medium tabular">{money(m.amount_minor)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </CardBody>
                  </Card>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </>
  )
}
