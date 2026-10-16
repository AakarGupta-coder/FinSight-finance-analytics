import { useMemo, useState } from 'react'
import { AlertTriangle, Eye, Lightbulb, Repeat, Sparkles, TrendingUp } from 'lucide-react'
import { useAppData } from '../lib/appData'
import { formatDate, formatMonth, shiftMonth } from '../lib/format'
import { useApi, useDocumentTitle } from '../lib/hooks'
import type { Insight, InsightsResponse } from '../lib/types'
import { Badge, Card, CardBody, CardHeader, EmptyState, ErrorState, PageHeader, Segmented, Select, Skeleton, StatCard } from '../components/ui/primitives'
import { InsightCard } from '../components/InsightCard'

type KindFilter = 'all' | Insight['kind']

export default function InsightsPage() {
  useDocumentTitle('Insights')
  const { today, money, categoryName } = useAppData()
  const current = today.slice(0, 7)
  const [month, setMonth] = useState(current)
  const [kind, setKind] = useState<KindFilter>('all')
  const { data, error, reload } = useApi<InsightsResponse>('/insights', { month })
  const months = useMemo(() => Array.from({ length: 12 }, (_, i) => shiftMonth(current, -i)), [current])
  const shown = data?.insights.filter((i) => kind === 'all' || i.kind === kind) ?? []

  return (
    <>
      <PageHeader title="Financial insights"
        description="Generated from your recorded transactions with transparent rules. Expand any insight to see the calculation and evidence."
        actions={<Select aria-label="Month" className="w-44" value={month} onChange={(e) => setMonth(e.target.value)}>
          {months.map((m) => <option key={m} value={m}>{formatMonth(m)}</option>)}
        </Select>} />

      {/* Summary strip: counts of the insights generated for the selected month. */}
      <div className="mb-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard emphasis icon={<AlertTriangle className="h-[18px] w-[18px]" />} label="Needs attention" loading={!data && !error}
          value={data ? data.insights.filter((i) => i.severity === 'critical' || i.severity === 'warning').length : 0} sub="Critical and warning insights" />
        <StatCard icon={<Eye className="h-[18px] w-[18px]" />} label="Observed facts" loading={!data && !error} value={data ? data.insights.filter((i) => i.kind === 'fact').length : 0} sub="Measured from your records" />
        <StatCard icon={<TrendingUp className="h-[18px] w-[18px]" />} label="Projections" loading={!data && !error} value={data ? data.insights.filter((i) => i.kind === 'projection').length : 0} sub="Based on your current pace" />
        <StatCard icon={<Lightbulb className="h-[18px] w-[18px]" />} label="Recommendations" loading={!data && !error} value={data ? data.insights.filter((i) => i.kind === 'recommendation').length : 0} sub="With the numbers behind them" />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3"><Segmented label="Insight type" size="sm" value={kind} onChange={setKind} options={[
          { value: 'all', label: 'All' }, { value: 'fact', label: 'Facts' }, { value: 'estimate', label: 'Estimates' },
          { value: 'projection', label: 'Projections' }, { value: 'recommendation', label: 'Recommendations' }]} />
        {data && <span className="text-xs text-muted">Period analysed: {data.generated_for.label} · {data.coverage.transactions_in_period} transaction(s) · history covers {data.coverage.months_with_data} month(s)</span>}
      </div>

      {error ? <Card><ErrorState error={error} onRetry={reload} /></Card> : (
        <div className="grid gap-4 xl:grid-cols-3">
          <div className="space-y-3 xl:col-span-2">
            {!data ? [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)
              : shown.length === 0 ? <Card><EmptyState icon={<Sparkles className="h-5 w-5" />} title="No insights of this type" description="Try another filter or month." /></Card>
              : shown.map((i) => <InsightCard key={i.id} insight={i} />)}
          </div>
          <div className="space-y-4">
            <Card>
              <CardHeader title="How to read insights" />
              <CardBody className="space-y-2 text-[13px] text-text-2">
                <p><Badge>Observed fact</Badge> Directly measured from your records.</p>
                <p><Badge tone="info">Estimate</Badge> A statistic such as an average.</p>
                <p><Badge tone="warning">Projection</Badge> Extrapolates your current pace; it may not happen.</p>
                <p><Badge tone="primary">Recommendation</Badge> A suggestion with the numbers behind it.</p>
                <p className="text-xs text-muted">Insights are informational and are not financial advice.</p>
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Recurring payments" description="Detected from similar amounts at regular intervals" />
              <CardBody>
                {!data ? <Skeleton className="h-24" /> : data.recurring.length === 0
                  ? <EmptyState icon={<Repeat className="h-5 w-5" />} title="None detected yet" description="Recurring payments are recognised after at least two similar, regularly spaced charges." className="py-4" />
                  : <ul className="divide-y divide-border">
                      {data.recurring.map((r) => (
                        <li key={r.key + r.category} className="py-2.5 text-[13px]">
                          <div className="flex justify-between gap-2"><span className="font-medium">{r.name}</span><span className="tabular font-semibold">{money(r.typical_amount_minor)}</span></div>
                          <p className="mt-0.5 text-xs text-muted">
                            {categoryName(r.category)} · {r.cadence} · {r.occurrences} payments{r.confidence === 'low' ? ' (low confidence)' : ''} ·{' '}
                            {r.active ? `next expected ~${formatDate(r.next_expected)}` : 'may have stopped'}
                          </p>
                        </li>
                      ))}
                    </ul>}
              </CardBody>
            </Card>
          </div>
        </div>
      )}
    </>
  )
}
