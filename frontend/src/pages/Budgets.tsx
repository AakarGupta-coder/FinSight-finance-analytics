import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { AlertTriangle, Bell, ChevronLeft, ChevronRight, Pencil, Plus, Trash2, TrendingUp, Wallet } from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'
import { formatDateTime, formatMonth, minorToInput, parseMoneyToMinor, shiftMonth } from '../lib/format'
import { useApi, useDocumentTitle } from '../lib/hooks'
import type { BudgetHistoryRow, BudgetOverview, BudgetRow } from '../lib/types'
import { Badge, Button, Card, CardBody, CardHeader, EmptyState, ErrorState, Field, Input, PageHeader, Progress, Select, Skeleton } from '../components/ui/primitives'
import { ConfirmDialog, Dialog } from '../components/ui/dialog'
import { MonthlyBars } from '../components/charts/Charts'
import { Donut } from '../components/charts/Donut'
import { categoryColor, cn } from '../lib/utils'
import { budgetTone } from './Dashboard'

function StatusBadge({ row }: { row: BudgetRow }) {
  if (row.status === 'exceeded') return <Badge tone="danger" icon={<AlertTriangle className="h-3 w-3" aria-hidden />}>Exceeded</Badge>
  if (row.status === 'at_limit') return <Badge tone="danger">At limit</Badge>
  if (row.projected_overrun) return <Badge tone="warning" icon={<TrendingUp className="h-3 w-3" aria-hidden />}>Projected overrun</Badge>
  if (row.status === 'warning') return <Badge tone="warning">Approaching limit</Badge>
  return <Badge tone="success">On track</Badge>
}

function BudgetDialog({ open, onOpenChange, mode, row, categories, onSaved }: {
  open: boolean; onOpenChange: (o: boolean) => void; mode: 'create-overall' | 'create-category' | 'edit'
  row?: BudgetRow | null; categories: { id: string; name: string }[]; onSaved: () => void
}) {
  const { currency } = useAppData()
  const [amount, setAmount] = useState(row ? minorToInput(row.amount_minor, currency) : '')
  const [category, setCategory] = useState(row?.category ?? categories[0]?.id ?? '')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const minor = parseMoneyToMinor(amount, currency)
    if (minor === null) {
      setError('Enter a valid amount (zero or more, at most 2 decimals).')
      return
    }
    setBusy(true)
    try {
      if (mode === 'edit' && row) await api.put(`/budgets/${row.budget_id}`, { amount_minor: minor })
      else await api.post('/budgets', { amount_minor: minor, category: mode === 'create-category' ? category : null })
      toast.success(mode === 'edit' ? 'Budget updated' : 'Budget created')
      onOpenChange(false)
      onSaved()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const title = mode === 'edit' ? `Edit ${row?.category_name} budget` : mode === 'create-overall' ? 'Set monthly budget' : 'Add category budget'
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={title} size="sm"
      description={mode === 'edit' ? 'The new amount applies from this month. Past months keep their original budget.' : 'Budgets repeat every month until changed.'}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        {mode === 'create-category' && (
          <Field label="Category" htmlFor="budget-category">
            <Select id="budget-category" value={category} onChange={(e) => setCategory(e.target.value)}>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </Field>
        )}
        <Field label={`Monthly amount (${currency})`} htmlFor="budget-amount" error={error ?? undefined}>
          <Input id="budget-amount" inputMode="decimal" autoFocus value={amount} onChange={(e) => { setAmount(e.target.value); setError(null) }} placeholder="0.00" aria-invalid={!!error} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button type="submit" loading={busy}>Save budget</Button>
        </div>
      </form>
    </Dialog>
  )
}

/** Overall budget: utilization donut + the key figures. */
function OverallHero({ row }: { row: BudgetRow }) {
  const { money } = useAppData()
  const over = Math.max(row.spent_minor - row.amount_minor, 0)
  const segs = over > 0 || row.amount_minor === 0
    ? [{ key: 'spent', label: 'Spent (budget fully used)', value: Math.max(row.amount_minor, row.spent_minor, 1), color: 'var(--danger)' }]
    : [{ key: 'spent', label: 'Spent', value: row.spent_minor, color: 'var(--series-single)' }, { key: 'left', label: 'Remaining', value: row.remaining_minor, color: 'var(--track)' }].filter((x) => x.value > 0)
  const figures: [string, string, string?][] = [
    ['Budget', money(row.amount_minor)],
    ['Spent', money(row.spent_minor)],
    [row.remaining_minor >= 0 ? 'Remaining' : 'Over budget', money(Math.abs(row.remaining_minor)), row.remaining_minor < 0 ? 'text-danger' : undefined],
    ['Projected month end', row.projected_spend_minor !== null ? money(row.projected_spend_minor, { round: true }) : '—', row.projected_overrun ? 'text-warning' : undefined],
  ]
  return (
    <div className="grid items-center gap-6 sm:grid-cols-[176px_1fr]">
      <Donut segments={segs} center={row.utilization_pct !== null ? `${row.utilization_pct}%` : '—'} caption={over > 0 ? 'over budget' : 'used'}
        ariaLabel={`Overall budget ${row.utilization_pct ?? 0} percent used`} />
      <div>
        <div className="mb-3"><StatusBadge row={row} /></div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
          {figures.map(([k, v, tone]) => (
            <div key={k}><dt className="text-xs text-muted">{k}</dt><dd className={cn('text-lg font-semibold tabular', tone)}>{v}</dd></div>
          ))}
        </dl>
        {row.daily_allowance_minor !== null && row.remaining_minor > 0 && (
          <p className="mt-3 rounded-lg bg-primary-soft px-3 py-2 text-[12.5px] text-primary">
            About <strong className="tabular">{money(row.daily_allowance_minor, { round: true })}</strong> per day left for the rest of the month.
          </p>
        )}
      </div>
    </div>
  )
}

/** Compact category budget card. */
function CategoryBudgetCard({ row, editable, onEdit, onDelete }: { row: BudgetRow; editable: boolean; onEdit: () => void; onDelete: () => void }) {
  const { money } = useAppData()
  return (
    <Card className="flex flex-col p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="h-2.5 w-2.5 shrink-0 rounded-[3px]" style={{ background: categoryColor(row.category ?? '') }} aria-hidden />
          <h3 className="truncate text-[14px] font-semibold">{row.category_name}</h3>
        </div>
        {editable && (
          <div className="-mr-1.5 -mt-1.5 flex">
            <Button variant="ghost" size="icon" className="h-8 w-8" aria-label={`Edit ${row.category_name} budget`} onClick={onEdit}><Pencil className="h-3.5 w-3.5" /></Button>
            <Button variant="ghost" size="icon" className="h-8 w-8" aria-label={`Delete ${row.category_name} budget`} onClick={onDelete}><Trash2 className="h-3.5 w-3.5" /></Button>
          </div>
        )}
      </div>
      <div className="mt-2 flex items-baseline justify-between gap-2">
        <p className="text-xl font-semibold tabular">{money(row.spent_minor)}</p>
        <p className="text-xs text-muted tabular">of {money(row.amount_minor)}</p>
      </div>
      <Progress className="mt-2" value={row.utilization_pct ?? (row.spent_minor > 0 ? 100 : 0)} tone={budgetTone(row.status, row.projected_overrun)} label={`${row.category_name} budget used`} />
      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2">
        <StatusBadge row={row} />
        <span className={cn('text-xs tabular', row.remaining_minor < 0 ? 'text-danger' : 'text-muted')}>
          {row.utilization_pct === null ? 'Zero budget' : `${row.utilization_pct}%`} · {row.remaining_minor >= 0 ? `${money(row.remaining_minor)} left` : `${money(-row.remaining_minor)} over`}
        </span>
      </div>
      {row.projected_spend_minor !== null && <p className="mt-1.5 text-[11.5px] text-muted">Projected {money(row.projected_spend_minor, { round: true })} by month end</p>}
    </Card>
  )
}

export default function BudgetsPage() {
  useDocumentTitle('Budgets')
  const { today, money, reference, me } = useAppData()
  const currentMonth = today.slice(0, 7)
  const [month, setMonth] = useState(currentMonth)
  const overview = useApi<BudgetOverview>('/budgets', { month })
  const history = useApi<{ months: BudgetHistoryRow[] }>('/budgets/history', { months: 6 })
  const [dialog, setDialog] = useState<{ mode: 'create-overall' | 'create-category' | 'edit'; row?: BudgetRow; preset?: string } | null>(null)
  const [deleting, setDeleting] = useState<BudgetRow | null>(null)
  const editable = month === currentMonth
  const data = overview.data

  const refresh = () => {
    overview.reload()
    history.reload()
  }
  const usedCats = new Set(data?.categories.map((c) => c.category) ?? [])
  const availableCats = (reference?.categories ?? []).filter((c) => !usedCats.has(c.id))
  const orderedCats = dialog?.preset ? [...availableCats].sort((a) => (a.id === dialog.preset ? -1 : 1)) : availableCats

  return (
    <>
      <PageHeader title="Budgets" description="Monthly limits, utilization and alerts."
        actions={<>
          <div className="flex h-9 items-center rounded-[10px] border border-border bg-surface-2">
            <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Previous month" onClick={() => setMonth(shiftMonth(month, -1))}><ChevronLeft className="h-4 w-4" /></Button>
            <span className="min-w-[120px] text-center text-[13px] font-medium">{formatMonth(month)}</span>
            <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Next month" disabled={month >= currentMonth} onClick={() => setMonth(shiftMonth(month, 1))}><ChevronRight className="h-4 w-4" /></Button>
          </div>
          {editable && <Button onClick={() => setDialog({ mode: 'create-category' })} disabled={!availableCats.length}><Plus className="h-4 w-4" aria-hidden />Category budget</Button>}
        </>} />

      {!editable && <p className="mb-4 rounded-lg bg-surface-2 px-4 py-2.5 text-[13px] text-muted">Viewing a past month with the budgets that applied then. Budgets can be changed for the current month onward.</p>}

      {overview.error ? <Card><ErrorState error={overview.error} onRetry={overview.reload} /></Card> : (
        <div className="space-y-4">
          {/* Row 1 — overall budget hero + alerts */}
          <div className="grid gap-4 xl:grid-cols-12">
            <Card className="xl:col-span-8">
              <CardHeader title="Overall monthly budget" description={data ? `${money(data.total_spent_minor)} spent in ${formatMonth(month)}` : undefined}
                action={data?.overall && editable && <>
                  <Button variant="ghost" size="icon" aria-label="Edit overall budget" onClick={() => setDialog({ mode: 'edit', row: data.overall! })}><Pencil className="h-4 w-4" /></Button>
                  <Button variant="ghost" size="icon" aria-label="Delete overall budget" onClick={() => setDeleting(data.overall)}><Trash2 className="h-4 w-4" /></Button>
                </>} />
              <CardBody>
                {!data ? <Skeleton className="h-44" /> : data.overall ? <OverallHero row={data.overall} /> : (
                  <EmptyState icon={<Wallet className="h-5 w-5" />} title="No overall budget" description="Set a monthly limit to track remaining budget and get alerts."
                    action={editable && <Button onClick={() => setDialog({ mode: 'create-overall' })}>Set monthly budget</Button>} />
                )}
              </CardBody>
            </Card>
            <Card className="xl:col-span-4">
              <CardHeader title="Alerts this month" action={<Link to="/app/settings" className="text-xs font-medium text-accent hover:underline">Thresholds</Link>} />
              <CardBody className="space-y-3">
                <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted">Alerting at
                  {(me?.preferences.budget_thresholds ?? []).map((t) => <Badge key={t} tone="neutral">{t}%</Badge>)}</div>
                {!data ? <Skeleton className="h-16" /> : data.alert_events.length === 0
                  ? <p className="flex items-center gap-2 text-[13px] text-muted"><Bell className="h-4 w-4" aria-hidden />No thresholds crossed.</p>
                  : <ul className="max-h-56 space-y-2 overflow-y-auto pr-1">
                      {data.alert_events.map((a, i) => (
                        <li key={i} className="flex gap-2.5 rounded-xl border border-border p-2.5 text-[13px]">
                          <span className={cn('mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg', a.threshold >= 100 ? 'bg-danger-soft text-danger' : 'bg-warning-soft text-warning')} aria-hidden><Bell className="h-3.5 w-3.5" /></span>
                          <div className="min-w-0">
                            <p><strong>{a.category_name}</strong> reached {a.threshold}%</p>
                            <p className="text-xs text-muted">{money(a.spent_minor)} of {money(a.budget_minor)} · {formatDateTime(a.created_at, me?.preferences.timezone)}</p>
                          </div>
                        </li>
                      ))}
                    </ul>}
              </CardBody>
            </Card>
          </div>

          {/* Row 2 — category budgets as compact cards */}
          <div>
            <div className="mb-2.5 flex items-end justify-between gap-2">
              <div><h2 className="text-[15px] font-semibold">Category budgets</h2><p className="text-[12.5px] text-muted">Sorted by utilization</p></div>
            </div>
            {!data ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-36" />)}</div>
              : data.categories.length === 0 ? (
                <Card><EmptyState title="No category budgets" description={editable ? 'Use Category budget above to add limits for categories like Food or Shopping.' : 'No category budgets applied in this month.'} /></Card>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {data.categories.map((row) => <CategoryBudgetCard key={row.budget_id} row={row} editable={editable}
                    onEdit={() => setDialog({ mode: 'edit', row })} onDelete={() => setDeleting(row)} />)}
                </div>
              )}
          </div>

          {/* Row 3 — history + unbudgeted */}
          <div className="grid items-start gap-4 xl:grid-cols-12">
            <Card className="xl:col-span-8">
              <CardHeader title="Budget history" description="Monthly spending against the overall budget that applied each month" />
              <CardBody>
                {history.error ? <ErrorState error={history.error} onRetry={history.reload} /> : !history.data ? <Skeleton className="h-60" /> : (
                  <>
                    <MonthlyBars height={200}
                      data={history.data.months.map((m) => ({ month: m.month, label: formatMonth(m.month, true), total_minor: m.spent_minor, by_category: {} }))}
                      budgetMinor={data?.overall?.amount_minor ?? null} />
                    <div className="mt-4 overflow-x-auto rounded-xl border border-border">
                      <table className="w-full text-[13px]">
                        <thead><tr className="border-b border-border bg-surface-2 text-left text-xs text-muted">
                          <th className="px-3 py-2 font-medium">Month</th><th className="px-3 py-2 text-right font-medium">Spent</th>
                          <th className="px-3 py-2 text-right font-medium">Budget</th><th className="px-3 py-2 text-right font-medium">Used</th><th className="px-3 py-2 font-medium">Result</th>
                        </tr></thead>
                        <tbody className="divide-y divide-border">
                          {history.data.months.map((m) => (
                            <tr key={m.month} className="transition-colors hover:bg-surface-2/60">
                              <td className="px-3 py-2">{formatMonth(m.month)}{m.is_current && <span className="text-muted"> (so far)</span>}</td>
                              <td className="px-3 py-2 text-right tabular">{money(m.spent_minor)}</td>
                              <td className="px-3 py-2 text-right tabular">{m.overall_budget_minor !== null ? money(m.overall_budget_minor) : '—'}</td>
                              <td className="px-3 py-2 text-right tabular">{m.utilization_pct !== null ? `${m.utilization_pct}%` : '—'}</td>
                              <td className="px-3 py-2">
                                {m.within_budget === null ? <span className="text-muted">No budget</span>
                                  : m.within_budget ? <Badge tone="success">Within budget</Badge> : <Badge tone="danger">Over budget</Badge>}
                                {m.categories_over_budget.length > 0 && <span className="ml-2 text-xs text-muted">{m.categories_over_budget.length} category budget(s) exceeded</span>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </CardBody>
            </Card>
            <Card className="xl:col-span-4">
              <CardHeader title="Spending without a budget" description={formatMonth(month)} />
              <CardBody>
                {!data ? <Skeleton className="h-16" /> : data.unbudgeted.length === 0
                  ? <p className="text-[13px] text-muted">All spending this month is covered by a category budget.</p>
                  : <ul className="divide-y divide-border">
                      {data.unbudgeted.map((u) => (
                        <li key={u.category} className="flex items-center justify-between gap-2 py-2 text-[13px]">
                          <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: categoryColor(u.category) }} aria-hidden />{u.category_name}</span>
                          <span className="flex items-center gap-2"><span className="font-medium tabular">{money(u.spent_minor)}</span>
                            {editable && <Button variant="outline" size="sm" onClick={() => setDialog({ mode: 'create-category', preset: u.category })}>Set budget</Button>}</span>
                        </li>
                      ))}
                    </ul>}
              </CardBody>
            </Card>
          </div>
        </div>
      )}

      {dialog && <BudgetDialog key={`${dialog.mode}-${dialog.row?.budget_id ?? dialog.preset ?? ''}`} open onOpenChange={(o) => !o && setDialog(null)}
        mode={dialog.mode} row={dialog.row} categories={orderedCats} onSaved={refresh} />}
      <ConfirmDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)} title={`Remove ${deleting?.category_name} budget?`}
        description="It stops applying from this month. Past months keep their history." confirmLabel="Remove budget"
        onConfirm={async () => {
          try {
            await api.del(`/budgets/${deleting!.budget_id}`)
            toast.success('Budget removed')
            refresh()
          } catch (err) {
            toast.error(errorMessage(err))
            throw err
          }
        }} />
    </>
  )
}
