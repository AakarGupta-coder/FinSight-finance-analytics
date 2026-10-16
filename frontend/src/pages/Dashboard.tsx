import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'
import {
  CalendarDays, ChevronLeft, ChevronRight, Database, Gauge, PiggyBank, Plus, ReceiptText, ScanLine, ShieldAlert, ShieldCheck,
  Target, TrendingUp, Wallet,
} from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'
import { formatDate, formatMonth, shiftMonth } from '../lib/format'
import { useApi, useDocumentTitle } from '../lib/hooks'
import type { BudgetHistoryRow, Dashboard, Goal } from '../lib/types'
import { categoryColor, cn, hasOwnSlot } from '../lib/utils'
import {
  AnimatedNumber, Badge, Button, ButtonLink, Card, CardHeader, CardLink, EmptyState, ErrorState, PageHeader, Progress, Segmented, Skeleton, StatCard, TrendChip,
} from '../components/ui/primitives'
import { TrendArea, type TrendPoint } from '../components/charts/Trend'
import { Donut, DonutLegend, type DonutSegment } from '../components/charts/Donut'
import { CategoryBars } from '../components/charts/Charts'
import { InsightCard } from '../components/InsightCard'
import { CategoryIcon } from '../components/CategoryIcon'

export function budgetTone(status?: string, projected?: boolean): 'primary' | 'success' | 'warning' | 'danger' {
  if (status === 'exceeded' || status === 'at_limit') return 'danger'
  if (status === 'warning' || projected) return 'warning'
  return 'success'
}

type Range = 'daily' | '6m' | '12m'
interface GoalsResponse { items: Goal[]; summary: { total_target_minor: number; total_saved_minor: number; required_monthly_minor: number; active_count: number; completed_count: number } }

/** Month picker styled like the reference's date-range control. */
function MonthPicker({ month, max, onChange }: { month: string; max: string; onChange: (m: string) => void }) {
  return (
    <div className="flex h-9 items-center rounded-[10px] border border-border bg-surface-2" role="group" aria-label="Choose month">
      <Button variant="ghost" size="icon" className="h-[34px] w-8 rounded-[9px]" aria-label="Previous month" onClick={() => onChange(shiftMonth(month, -1))}><ChevronLeft className="h-4 w-4" /></Button>
      <span className="flex min-w-[120px] items-center justify-center gap-1.5 text-[13px] text-text-2" aria-live="polite">
        <CalendarDays className="h-3.5 w-3.5 text-muted" aria-hidden />{formatMonth(month)}
      </span>
      <Button variant="ghost" size="icon" className="h-[34px] w-8 rounded-[9px]" aria-label="Next month" disabled={month >= max} onClick={() => onChange(shiftMonth(month, 1))}><ChevronRight className="h-4 w-4" /></Button>
    </div>
  )
}

export default function DashboardPage() {
  useDocumentTitle('Dashboard')
  const { today, money, me, reload: reloadMe, categoryName } = useAppData()
  const currentMonth = today.slice(0, 7)
  const [month, setMonth] = useState(currentMonth)
  const [range, setRange] = useState<Range>('daily')
  const { data, error, reload, loading } = useApi<Dashboard>('/dashboard', { month })
  const goals = useApi<GoalsResponse>('/goals')
  const history = useApi<{ months: BudgetHistoryRow[] }>(range === 'daily' ? null : '/budgets/history', { months: range === '12m' ? 12 : 6 })
  const navigate = useNavigate()
  const [seeding, setSeeding] = useState(false)

  const loadDemo = async () => {
    setSeeding(true)
    try {
      await api.post('/demo-data')
      toast.success('Demo data loaded', { description: 'Synthetic records are labelled “Demo”. Remove them any time in Settings.' })
      await reloadMe()
      reload()
      goals.reload()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSeeding(false)
    }
  }

  // The page's single Add expense action lives here.
  const header = (
    <PageHeader
      title="Dashboard"
      description={`Spending, budget and savings overview · ${formatMonth(month)}${month === currentMonth ? ' so far' : ''}`}
      actions={<>
        <MonthPicker month={month} max={currentMonth} onChange={setMonth} />
        <ButtonLink to="/app/transactions/new"><Plus className="h-4 w-4" aria-hidden />Add expense</ButtonLink>
      </>}
    />
  )

  const d = data
  const s = d?.summary
  // Switching month keeps the previous figures on screen, dimmed, until the new ones arrive.
  const refresh = cn('fs-refreshable', loading && d && 'fs-refreshing')

  /* ---- trend data (all from API responses; nothing synthesised) ---- */
  const trend: TrendPoint[] = useMemo(() => {
    if (range === 'daily') {
      return (d?.daily ?? []).map((p) => ({ key: p.date, label: formatDate(p.date, { year: false }), title: formatDate(p.date), value: p.amount_minor }))
    }
    return (history.data?.months ?? []).map((m) => ({
      key: m.month, label: formatMonth(m.month, true), title: `${formatMonth(m.month)}${m.is_current ? ' (so far)' : ''}`,
      value: m.spent_minor, reference: m.overall_budget_minor,
    }))
  }, [range, d, history.data])
  const trendTotal = trend.reduce((a, p) => a + p.value, 0)
  const peak = trend.reduce<TrendPoint | null>((best, p) => (!best || p.value > best.value ? p : best), null)

  /* ---- spending donut: real category totals; segments sum to the centre total ---- */
  const spending = useMemo(() => {
    const rows = d?.categories ?? []
    const total = rows.reduce((a, r) => a + r.amount_minor, 0)
    const named = rows.filter((r) => hasOwnSlot(r.category)).slice(0, 5)
    const folded = rows.filter((r) => !named.includes(r))
    const segs: DonutSegment[] = named.map((r) => ({ key: r.category, label: r.category_name, value: r.amount_minor, color: categoryColor(r.category) }))
    const otherTotal = folded.reduce((a, r) => a + r.amount_minor, 0)
    if (otherTotal > 0) segs.push({ key: '__other', label: folded.length === 1 ? folded[0].category_name : `Other (${folded.length})`, value: otherTotal, color: 'var(--series-other)' })
    return { total, segs }
  }, [d])

  /* ---- budget summary: overall budget, else the sum of category budgets ---- */
  const budget = useMemo(() => {
    const b = d?.budget
    if (!b) return null
    if (b.overall) {
      const o = b.overall
      return { label: 'Monthly budget', amount: o.amount_minor, spent: o.spent_minor, remaining: o.remaining_minor, util: o.utilization_pct,
        tone: budgetTone(o.status, o.projected_overrun), projected: o.projected_spend_minor, projectedOverrun: o.projected_overrun,
        allowance: o.daily_allowance_minor }
    }
    if (!b.categories.length) return null
    const amount = b.categories.reduce((a, c) => a + c.amount_minor, 0)
    const spent = b.categories.reduce((a, c) => a + c.spent_minor, 0)
    const util = amount ? Math.round((spent / amount) * 1000) / 10 : null
    return { label: `${b.categories.length} category budget(s)`, amount, spent, remaining: amount - spent, util,
      tone: (util !== null && util >= 100 ? 'danger' : util !== null && util >= 80 ? 'warning' : 'success') as ReturnType<typeof budgetTone>,
      projected: null, projectedOverrun: false, allowance: null }
  }, [d])

  if (error) return <>{header}<Card><ErrorState error={error} onRetry={reload} /></Card></>

  const isEmptyAccount = d && d.monthly.every((m) => m.total_minor === 0) && d.goals.length === 0
  const hasDemo = d?.recent_transactions.some((t) => t.is_demo) || d?.goals.some((g) => g.is_demo)

  if (d && isEmptyAccount && month === currentMonth) {
    return (
      <>
        {header}
        <Card variant="featured">
          <EmptyState
            icon={<Wallet className="h-5 w-5" />}
            title={`Welcome${me?.user.name ? `, ${me.user.name}` : ''}! Let's set up your finances`}
            description="Your dashboard fills in as you record expenses. Use Add expense above, scan a receipt or set a monthly budget to get started."
            action={<>
              <Button variant="outline" onClick={() => navigate('/app/receipts')}><ScanLine className="h-4 w-4" aria-hidden />Scan a receipt</Button>
              <Button variant="outline" onClick={() => navigate('/app/budgets')}><Wallet className="h-4 w-4" aria-hidden />Set a budget</Button>
              {me?.demo_data_enabled && <Button variant="ghost" loading={seeding} onClick={loadDemo}><Database className="h-4 w-4" aria-hidden />Explore with demo data</Button>}
            </>}
          />
        </Card>
      </>
    )
  }

  const g = goals.data?.summary
  const goalPct = g && g.total_target_minor ? Math.round((g.total_saved_minor / g.total_target_minor) * 1000) / 10 : null
  const catBudgets = d ? [...d.budget.categories].sort((a, b) => (b.utilization_pct ?? 0) - (a.utilization_pct ?? 0)).slice(0, 5) : []

  return (
    <>
      {header}
      {hasDemo && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-surface-2 px-4 py-2 text-[12.5px] text-text-2">
          <span><strong className="font-medium text-text">Demo data is loaded.</strong> These synthetic records are labelled “Demo”.</span>
          <Link to="/app/settings" className="font-medium text-accent hover:underline">Manage in Settings</Link>
        </div>
      )}

      {/* Row 1 — KPI cards */}
      <div className={cn('grid gap-4 sm:grid-cols-2 xl:grid-cols-3', refresh)} aria-busy={loading || undefined}>
        <StatCard icon={<ReceiptText />} loading={!d}
          label={month === currentMonth ? 'Total spent this month' : `Total spent · ${formatMonth(month, true)}`}
          value={<AnimatedNumber value={s?.total_minor ?? 0} format={(v) => money(v)} />}
          chip={s && s.change_pct !== null ? <TrendChip value={s.change_pct} label={`Change versus ${s.comparison_period.label}`} /> : null}
          sub={s ? (s.change_pct === null ? 'No spending in the comparison period' : `vs ${money(s.previous_comparable_total_minor)} · ${s.comparison_period.label}`) : null} />
        <StatCard icon={<Gauge />} loading={!d}
          label="Average per day" value={<AnimatedNumber value={s?.average_daily_minor ?? 0} format={(v) => money(v, { round: true })} />}
          sub={s ? `${s.transaction_count} transaction(s) over ${s.days_elapsed} day(s)${s.largest_expense ? ` · largest ${money(s.largest_expense.amount_minor)}` : ''}` : null} />
        <StatCard icon={<PiggyBank />} loading={!goals.data && !goals.error}
          label="Saved toward goals" value={g && g.total_target_minor ? <AnimatedNumber value={g.total_saved_minor} format={(v) => money(v)} /> : 'No goals yet'}
          chip={goalPct !== null ? <Badge tone="primary">{goalPct}% of target</Badge> : null}
          sub={g && g.total_target_minor
            ? `of ${money(g.total_target_minor)} · ${g.active_count} active goal(s)`
            : <Link to="/app/goals" className="font-medium text-accent hover:underline">Create a savings goal</Link>} />
      </div>

      {/* Row 2 — category split + budgets (one card, two panes) | remaining budget (featured) */}
      <div className={cn('mt-4 grid gap-4 xl:grid-cols-12', refresh)}>
        <Card className="grid xl:col-span-8 md:grid-cols-2 md:divide-x md:divide-border max-md:divide-y max-md:divide-border">
          <section aria-labelledby="dash-cats" className="flex flex-col">
            <CardHeader title={<span id="dash-cats">Spending by category</span>} description={formatMonth(month)} action={<CardLink to="/app/analytics">Analytics</CardLink>} />
            <div className="flex-1 px-5 pb-5">
              {!d ? <Skeleton className="h-40" /> : spending.total === 0 ? <EmptyState title="No spending yet" description="Category totals appear once you add expenses." className="py-6" /> : (
                <div className="grid items-center gap-4 sm:grid-cols-[148px_1fr]">
                  <Donut size={148} segments={spending.segs} center={money(spending.total, { compact: spending.total >= 100_000_00 })} caption="Total spent"
                    ariaLabel={`Spending by category, total ${money(spending.total)}`} />
                  {/* Shares are in the donut tooltip; the legend keeps label + amount so names are not truncated. */}
                  <DonutLegend rows={spending.segs.map((x) => ({ key: x.key, label: x.label, color: x.color, value: money(x.value) }))} />
                </div>
              )}
            </div>
          </section>
          <section aria-labelledby="dash-budgets" className="flex flex-col">
            <CardHeader title={<span id="dash-budgets">{catBudgets.length ? 'Category budgets' : 'Top categories'}</span>}
              description={catBudgets.length ? 'Highest utilization first' : 'Share of this month’s spending'} action={<CardLink to="/app/budgets">Budgets</CardLink>} />
            <div className="flex-1 px-5 pb-5">
              {!d ? <Skeleton className="h-40" /> : catBudgets.length ? (
                <ul className="space-y-3" aria-label="Category budgets">
                  {catBudgets.map((c) => (
                    <li key={c.budget_id}>
                      <div className="flex items-baseline justify-between gap-2 text-[12.5px]">
                        <span className="flex min-w-0 items-center gap-2 text-text-2">
                          <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: categoryColor(c.category ?? '') }} aria-hidden />
                          <span className="truncate">{c.category_name}</span>
                        </span>
                        <span className="shrink-0 tabular text-text">{money(c.spent_minor)} <span className="text-muted">/ {money(c.amount_minor)}</span></span>
                      </div>
                      <Progress className="mt-1.5" value={c.utilization_pct ?? (c.spent_minor > 0 ? 100 : 0)} tone={budgetTone(c.status, c.projected_overrun)} label={`${c.category_name} budget used`} />
                    </li>
                  ))}
                </ul>
              ) : spending.total === 0 ? <p className="py-6 text-center text-[12.5px] text-muted">Nothing recorded for {formatMonth(month)}.</p>
                : <CategoryBars rows={d.categories} limit={5} />}
            </div>
          </section>
        </Card>

        <Card variant="featured" className="flex flex-col p-5 xl:col-span-4">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[13px] text-text-2">{budget && budget.remaining < 0 ? 'Over budget' : 'Remaining budget'}</p>
              <p className="text-[11.5px] text-muted">{budget ? budget.label : 'No budget set'} · {formatMonth(month, true)}</p>
            </div>
            {budget && budget.util !== null && <Badge tone={budget.tone === 'success' ? 'success' : budget.tone}>{budget.util}% used</Badge>}
          </div>
          {!d ? <Skeleton className="mt-4 h-24" /> : budget ? (
            <>
              <p className={cn('mt-4 text-[34px] font-semibold leading-none tracking-tight tabular', budget.remaining < 0 ? 'text-danger' : 'text-text')}>
                <AnimatedNumber value={Math.abs(budget.remaining)} format={(v) => money(v)} />
              </p>
              <p className="mt-1.5 text-[12.5px] text-muted">of {money(budget.amount)} · {money(budget.spent)} spent</p>
              <Progress className="mt-4 h-2" value={budget.util ?? 100} tone={budget.tone} label="Budget used" />
              <dl className="mt-4 grid grid-cols-2 gap-3 text-[12px]">
                <div className="rounded-xl border border-border bg-surface-2/70 p-2.5">
                  <dt className="text-muted">Projected month end</dt>
                  <dd className={cn('mt-0.5 text-[14px] font-medium tabular', budget.projectedOverrun ? 'text-warning' : 'text-text')}>{budget.projected !== null ? money(budget.projected, { round: true }) : '—'}</dd>
                </div>
                <div className="rounded-xl border border-border bg-surface-2/70 p-2.5">
                  <dt className="text-muted">Left per day</dt>
                  <dd className="mt-0.5 text-[14px] font-medium tabular text-text">{budget.allowance !== null && budget.remaining > 0 ? money(budget.allowance, { round: true }) : '—'}</dd>
                </div>
              </dl>
              <div className="mt-auto pt-4"><ButtonLink to="/app/budgets" variant="outline" size="sm"><Wallet className="h-3.5 w-3.5" aria-hidden />Manage budgets</ButtonLink></div>
            </>
          ) : (
            <>
              <p className="mt-4 text-[13px] leading-relaxed text-text-2">Set a monthly or category budget to see what is left, your projected month-end spend and a daily allowance.</p>
              <div className="mt-auto pt-4"><ButtonLink to="/app/budgets" variant="outline" size="sm"><Wallet className="h-3.5 w-3.5" aria-hidden />Set a budget</ButtonLink></div>
            </>
          )}
        </Card>
      </div>

      {/* Row 3 — spending trend (main chart) | recent activity */}
      <div className={cn('mt-4 grid gap-4 xl:grid-cols-12', refresh)}>
        <Card className="flex flex-col xl:col-span-8">
          <div className="flex flex-wrap items-start justify-between gap-3 px-5 pt-4">
            <div className="min-w-0">
              <h2 className="text-[14px] font-medium text-text">Spending trend</h2>
              {trendTotal > 0 ? (
                <p className="mt-1.5 text-[26px] font-semibold leading-none tracking-tight tabular"><AnimatedNumber value={trendTotal} format={(v) => money(v)} /></p>
              ) : null}
              <p className="mt-1.5 text-[12px] text-muted">
                {range === 'daily'
                  ? (s ? `Daily · ${formatDate(s.period_start)} – ${formatDate(s.period_end)}` : 'Daily')
                  : history.data?.months.length
                    ? `Monthly · ${formatMonth(history.data.months[0].month, true)} – ${formatMonth(history.data.months[history.data.months.length - 1].month, true)} (latest month so far)`
                    : 'Monthly'}
                {trendTotal > 0 && peak && <> · avg {money(Math.round(trendTotal / Math.max(trend.length, 1)), { round: true })}/{range === 'daily' ? 'day' : 'month'} · peak {money(peak.value)} on {peak.label}</>}
              </p>
            </div>
            <Segmented label="Time range" size="sm" value={range} onChange={setRange}
              options={[{ value: 'daily', label: 'Daily' }, { value: '6m', label: '6M' }, { value: '12m', label: '12M' }]} />
          </div>
          <div className="flex-1 px-3 pb-4 pt-3 sm:px-4">
            {range !== 'daily' && history.error ? <ErrorState error={history.error} onRetry={history.reload} />
              : (range === 'daily' ? !d : !history.data) ? <Skeleton className="mx-2 h-[292px]" />
              : trendTotal === 0 ? <EmptyState icon={<TrendingUp className="h-5 w-5" />} title="No spending in this period" description="Recorded expenses will appear here as a trend." />
              : <TrendArea height={292} data={trend} valueLabel="Spending" referenceLabel={range === 'daily' ? undefined : 'Monthly budget'} />}
          </div>
        </Card>

        <Card className="flex flex-col xl:col-span-4">
          <CardHeader title="Recent activity" description={formatMonth(month)} action={<CardLink to="/app/transactions">View all</CardLink>} />
          <div className="flex-1 pb-2">
            {!d ? <div className="space-y-2 px-5">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-11" />)}</div>
              : d.recent_transactions.length === 0 ? <EmptyState title="No transactions this month" description="Expenses you add appear here." className="py-8" />
              : (
                <ul>
                  {d.recent_transactions.slice(0, 6).map((t) => (
                    <li key={t.id}>
                      <Link to={`/app/transactions?open=${t.id}`} className="flex items-center gap-3 px-5 py-2.5 transition-colors hover:bg-surface-2">
                        <CategoryIcon category={t.category} />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-[13px] font-medium text-text">{t.description}{t.is_demo && <Badge className="ml-1.5 align-middle">Demo</Badge>}</p>
                          <p className="truncate text-[11.5px] text-muted">{categoryName(t.category)}{t.merchant ? ` · ${t.merchant}` : ''}</p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="text-[13px] font-semibold tabular text-text">{money(t.amount_minor)}</p>
                          <p className="text-[11px] text-muted">{formatDate(t.date, { year: false })}</p>
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
          </div>
        </Card>
      </div>

      {/* Row 4 — insights | needs attention */}
      <div className={cn('mt-4 grid items-start gap-4 xl:grid-cols-12', refresh)}>
        <Card className="xl:col-span-8">
          <CardHeader title="Financial insights" description="Generated from your records with transparent rules" action={<CardLink to="/app/insights">All insights</CardLink>} />
          <div className="grid gap-2.5 px-5 pb-5 lg:grid-cols-2">
            {!d ? [0, 1].map((i) => <Skeleton key={i} className="h-24" />)
              : d.insights.length === 0 ? <EmptyState title="No insights yet" description="Insights appear as your history grows." className="py-6 lg:col-span-2" />
              : d.insights.slice(0, 4).map((i) => <InsightCard key={i.id} insight={i} compact />)}
          </div>
        </Card>
        <Card className="xl:col-span-4">
          <CardHeader title="Needs attention" description="Unusual transactions and goal deadlines"
            action={d && d.anomalies.open_count > 0 ? <CardLink to="/app/anomalies">Review {d.anomalies.open_count}</CardLink> : null} />
          <div className="space-y-4 px-5 pb-5">
            {!d ? <Skeleton className="h-16" /> : d.anomalies.items.length === 0
              ? <p className="flex items-center gap-2 text-[12.5px] text-muted"><ShieldCheck className="h-4 w-4 text-success" aria-hidden />No transactions need review.</p>
              : <ul className="space-y-2">
                  {d.anomalies.items.map((a) => (
                    <li key={a.id} className="flex gap-2.5 rounded-xl border border-border bg-surface-2 p-2.5">
                      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-warning-soft text-warning" aria-hidden><ShieldAlert className="h-3.5 w-3.5" /></span>
                      <div className="min-w-0 flex-1">
                        <div className="flex justify-between gap-2 text-[12.5px]"><span className="truncate font-medium">{a.expense?.description}</span><span className="shrink-0 font-semibold tabular">{money(a.expense?.amount_minor)}</span></div>
                        <p className="mt-0.5 line-clamp-2 text-[11.5px] text-muted">{a.reason}</p>
                      </div>
                    </li>
                  ))}
                </ul>}
            {d && d.upcoming_targets.length > 0 && (
              <div className="border-t border-border pt-3">
                <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted">Upcoming goal targets</p>
                <ul className="mt-2 space-y-2 text-[12.5px]">
                  {d.upcoming_targets.map((t) => (
                    <li key={t.id} className="flex items-center gap-2.5">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-text-2" aria-hidden><Target className="h-3.5 w-3.5" /></span>
                      <span className="min-w-0 flex-1 truncate">{t.name}</span>
                      <span className="shrink-0 tabular text-muted">{formatDate(t.target_date)}{t.required_monthly_minor ? ` · ${money(t.required_monthly_minor, { round: true })}/mo` : ''}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Card>
      </div>
    </>
  )
}
