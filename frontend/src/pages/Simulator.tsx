import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { FlaskConical, Info, Plus, Target, Trash2, Trophy } from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'
import { formatDate, parseMoneyToMinor } from '../lib/format'
import { useApi, useDebounced, useDocumentTitle } from '../lib/hooks'
import { cn } from '../lib/utils'
import type { Goal, SimulationResponse } from '../lib/types'
import { AnimatedNumber, Badge, Button, Card, CardBody, CardHeader, EmptyState, Field, Input, PageHeader, Select, Skeleton } from '../components/ui/primitives'

type Mode = 'percent' | 'amount' | 'target'
interface Adj { category: string; mode: Mode; value: string }
interface Scenario { name: string; adjustments: Adj[] }
type Baseline = 'avg_3_months' | 'last_month' | 'current_month_projection'

interface RequiredResult {
  goal_completed: boolean; message?: string; label?: string; amount_minor?: number; months?: number; required_monthly_minor: number
  baseline_total_minor?: number; required_reduction_pct?: number | null; feasible?: boolean; explanation?: string
}

function AdjustmentEditor({ adj, onChange, onRemove, categories, currency }: {
  adj: Adj; onChange: (a: Adj) => void; onRemove?: () => void; categories: { id: string; name: string }[]; currency: string
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] gap-2 rounded-xl border border-border bg-surface-2 p-2.5">
      <Select aria-label="Category" value={adj.category} onChange={(e) => onChange({ ...adj, category: e.target.value })}>
        {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </Select>
      <Select aria-label="Change type" value={adj.mode} onChange={(e) => onChange({ ...adj, mode: e.target.value as Mode, value: e.target.value === 'percent' ? '20' : '' })} className="">
        <option value="percent">Reduce by %</option>
        <option value="amount">Reduce by amount</option>
        <option value="target">Set monthly amount</option>
      </Select>
      {onRemove ? <Button variant="ghost" size="icon" aria-label="Remove change" onClick={onRemove}><Trash2 className="h-4 w-4" /></Button> : <span className="w-9" />}
      <div className="col-span-3 flex items-center gap-2">
        {adj.mode === 'percent' ? <>
          <input type="range" min={0} max={100} step={1} aria-label="Reduction percentage" value={Number(adj.value) || 0}
            onChange={(e) => onChange({ ...adj, value: e.target.value })} className="w-full accent-[var(--primary)]" />
          <span className="w-10 text-right text-[13px] tabular">{adj.value || 0}%</span>
        </> : <Input aria-label={`Amount (${currency})`} inputMode="decimal" placeholder={`Amount (${currency})`} value={adj.value} onChange={(e) => onChange({ ...adj, value: e.target.value })} />}
      </div>
    </div>
  )
}

export default function SimulatorPage() {
  useDocumentTitle('What-If simulator')
  const { reference, money, currency } = useAppData()
  const [params] = useSearchParams()
  const categories = reference?.categories ?? []
  const initialCategory = params.get('category') ?? 'food'
  const initialPercent = params.get('percent') ?? '20'
  const [baseline, setBaseline] = useState<Baseline>('avg_3_months')
  const [goalId, setGoalId] = useState('')
  const [scenarios, setScenarios] = useState<Scenario[]>([
    { name: 'Scenario A', adjustments: [{ category: initialCategory, mode: 'percent', value: initialPercent }] },
    { name: 'Scenario B', adjustments: [{ category: 'shopping', mode: 'amount', value: '1000' }] },
  ])
  const goals = useApi<{ items: Goal[] }>('/goals')
  const [result, setResult] = useState<SimulationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const payload = useMemo(() => {
    const problems: string[] = []
    const body = {
      baseline,
      goal_id: goalId || null,
      scenarios: scenarios.map((s) => ({
        name: s.name || 'Scenario',
        adjustments: s.adjustments.map((a) => {
          let value: string | number = a.value
          if (a.mode === 'percent') {
            const n = Number(a.value)
            if (!(n >= 0 && n <= 100)) problems.push('Percentages must be between 0 and 100.')
            value = n
          } else {
            const minor = parseMoneyToMinor(a.value, currency)
            if (minor === null) problems.push(`Enter a valid amount for ${categories.find((c) => c.id === a.category)?.name ?? a.category}.`)
            value = minor ?? 0
          }
          return { category: a.category, mode: a.mode, value }
        }),
      })),
    }
    const dupes = scenarios.some((s) => new Set(s.adjustments.map((a) => a.category)).size !== s.adjustments.length)
    if (dupes) problems.push('Each category can appear only once per scenario.')
    return { body, problems }
  }, [baseline, goalId, scenarios, currency, categories])
  const debounced = useDebounced(payload, 300)

  useEffect(() => {
    if (debounced.problems.length) {
      setError(debounced.problems[0])
      return
    }
    let cancelled = false
    setLoading(true)
    api.post<SimulationResponse>('/simulations', debounced.body)
      .then((r) => { if (!cancelled) { setResult(r); setError(null) } })
      .catch((err) => !cancelled && setError(errorMessage(err)))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [debounced])

  const update = (i: number, s: Scenario) => setScenarios((all) => all.map((x, j) => (j === i ? s : x)))
  const nextCategory = (s: Scenario) => categories.find((c) => !s.adjustments.some((a) => a.category === c.id))?.id ?? categories[0]?.id

  // Required savings for a goal / custom target
  const [reqGoal, setReqGoal] = useState('')
  const [reqTarget, setReqTarget] = useState('')
  const [reqMonths, setReqMonths] = useState('12')
  const [required, setRequired] = useState<RequiredResult | null>(null)
  const [reqError, setReqError] = useState<string | null>(null)
  const calcRequired = async () => {
    setReqError(null)
    try {
      const body = reqGoal ? { goal_id: reqGoal, baseline } : { target_minor: parseMoneyToMinor(reqTarget, currency), months: Number(reqMonths), baseline }
      setRequired(await api.post<RequiredResult>('/simulations/required-savings', body))
    } catch (err) {
      setRequired(null)
      setReqError(errorMessage(err))
    }
  }

  const activeGoals = goals.data?.items.filter((g) => !g.archived) ?? []
  return (
    <>
      <PageHeader title="What-If simulator" description="Explore hypothetical changes to your spending. Nothing here changes your real records." />
      <div className="mb-4 flex items-start gap-2 rounded-xl border border-border bg-surface-2 px-4 py-2.5 text-[12.5px] text-text-2">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>Results are estimates based on your past spending. Annual figures assume the monthly change continues for 12 months.</span>
      </div>

      <div className="grid gap-4 xl:grid-cols-12">
        <div className="space-y-4 xl:col-span-5">
          <Card>
            <CardHeader title="Settings" />
            <CardBody className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
              <Field label="Compare against" htmlFor="baseline" hint="Your 'current' monthly spending per category">
                <Select id="baseline" value={baseline} onChange={(e) => setBaseline(e.target.value as Baseline)}>
                  <option value="avg_3_months">Average of last 3 months</option>
                  <option value="last_month">Last month</option>
                  <option value="current_month_projection">This month (projected)</option>
                </Select>
              </Field>
              <Field label="Apply savings to a goal" htmlFor="goal" hint="Optional">
                <Select id="goal" value={goalId} onChange={(e) => setGoalId(e.target.value)}>
                  <option value="">No goal</option>
                  {activeGoals.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
                </Select>
              </Field>
            </CardBody>
          </Card>
          {scenarios.map((s, i) => (
            <Card key={i}>
              <CardHeader title={<Input aria-label="Scenario name" value={s.name} maxLength={60} onChange={(e) => update(i, { ...s, name: e.target.value })} className="h-8 w-48 font-semibold" />}
                action={scenarios.length > 1 && <Button variant="ghost" size="sm" onClick={() => setScenarios((all) => all.filter((_, j) => j !== i))}><Trash2 className="h-3.5 w-3.5" aria-hidden />Remove</Button>} />
              <CardBody className="space-y-2">
                {s.adjustments.map((a, k) => (
                  <AdjustmentEditor key={k} adj={a} categories={categories} currency={currency}
                    onChange={(na) => update(i, { ...s, adjustments: s.adjustments.map((x, m) => (m === k ? na : x)) })}
                    onRemove={s.adjustments.length > 1 ? () => update(i, { ...s, adjustments: s.adjustments.filter((_, m) => m !== k) }) : undefined} />
                ))}
                <Button variant="ghost" size="sm" disabled={s.adjustments.length >= categories.length}
                  onClick={() => update(i, { ...s, adjustments: [...s.adjustments, { category: nextCategory(s), mode: 'percent', value: '10' }] })}>
                  <Plus className="h-3.5 w-3.5" aria-hidden />Add another category
                </Button>
              </CardBody>
            </Card>
          ))}
          {scenarios.length < 4 && <Button variant="outline" className="w-full justify-center" onClick={() => setScenarios((all) => [...all, { name: `Scenario ${String.fromCharCode(65 + all.length)}`, adjustments: [{ category: 'entertainment', mode: 'percent', value: '25' }] }])}>
            <Plus className="h-4 w-4" aria-hidden />Add scenario to compare</Button>}
        </div>

        <div className="space-y-4 xl:col-span-7" aria-live="polite">
          {error && <p role="alert" className="fs-field-msg rounded-lg bg-danger-soft px-3 py-2 text-[13px] text-danger">{error}</p>}
          {!result ? <Skeleton className="h-72" /> : (
            <>
              <Card className={cn('fs-refreshable', loading && 'fs-refreshing')}>
                <CardHeader title="Comparison" description={`Baseline: ${result.baseline.label} · ${money(result.baseline.total_minor)} per month`}
                  action={<Badge tone="warning">Hypothetical</Badge>} />
                <CardBody className="overflow-x-auto">
                  {result.baseline.total_minor === 0 ? <EmptyState icon={<FlaskConical className="h-5 w-5" />} title="No spending in the baseline period" description="Choose a different baseline or record expenses first." /> : (
                    <table className="w-full text-[13px]">
                      <thead><tr className="border-b border-border text-left text-xs text-muted">
                        <th className="py-2 font-medium">Scenario</th><th className="py-2 text-right font-medium">Current / month</th>
                        <th className="py-2 text-right font-medium">New / month</th><th className="py-2 text-right font-medium">Saves / month</th><th className="py-2 text-right font-medium">Saves / year*</th>
                      </tr></thead>
                      <tbody className="divide-y divide-border">
                        {result.scenarios.map((s) => (
                          <tr key={s.name}>
                            <td className="py-2 font-medium">{s.name} {result.best_scenario === s.name && <Badge tone="success" icon={<Trophy className="h-3 w-3" aria-hidden />}>Most savings</Badge>}</td>
                            <td className="py-2 text-right tabular">{money(s.current_total_minor)}</td>
                            <td className="py-2 text-right tabular">{money(s.new_total_minor)}</td>
                            <td className={`py-2 text-right font-semibold tabular ${s.monthly_savings_minor < 0 ? 'text-danger' : 'text-success'}`}><AnimatedNumber value={s.monthly_savings_minor} format={(v) => money(v)} duration={450} /></td>
                            <td className="py-2 text-right tabular"><AnimatedNumber value={s.annual_savings_minor} format={(v) => money(v)} duration={450} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  <p className="mt-2 text-xs text-muted">* Assumes the monthly change continues for 12 months.</p>
                </CardBody>
              </Card>
              <div className={cn('fs-refreshable grid gap-4 lg:grid-cols-2', loading && 'fs-refreshing')}>
                {result.scenarios.map((s) => (
                  <Card key={s.name} variant="muted" className="border-dashed p-4">
                    <h3 className="text-sm font-semibold">{s.name}</h3>
                    <ul className="mt-2 divide-y divide-border text-[13px]">
                      {s.rows.map((r) => (
                        <li key={r.category} className="py-1.5">
                          <div className="flex justify-between"><span>{r.category_name}</span><span className="tabular">{money(r.current_minor)} → <strong>{money(r.new_minor)}</strong></span></div>
                          <p className="text-xs text-muted">{r.mode === 'percent' ? `Reduce by ${r.value}%` : r.mode === 'amount' ? `Reduce by ${money(Number(r.value))}` : `Set to ${money(Number(r.value))}`} · {money(r.monthly_savings_minor)}/month</p>
                        </li>
                      ))}
                    </ul>
                    {s.budget && <p className="mt-2 text-xs text-text-2">Remaining monthly budget: {money(s.budget.remaining_current_minor)} → <strong>{money(s.budget.remaining_new_minor)}</strong> (budget {money(s.budget.budget_minor)})</p>}
                    {s.goal && (
                      <div className="mt-2 rounded-lg bg-surface-2 p-2.5 text-xs">
                        <p className="font-medium">Goal: {s.goal.name}</p>
                        <p className="mt-0.5 text-text-2">{s.goal.months_to_goal === null ? 'No savings to apply to this goal.' : s.goal.months_to_goal === 0 ? 'Goal already reached.'
                          : `About ${s.goal.months_to_goal} month(s) to reach it (≈ ${formatDate(s.goal.estimated_completion)}) at ${money(s.goal.monthly_with_savings_minor)}/month.`}
                          {s.goal.required_monthly_minor !== null && (s.goal.meets_target_date ? ' Meets the target date.' : ` Needs ${money(s.goal.required_monthly_minor)}/month to meet the target date.`)}</p>
                        <p className="mt-1 text-muted">{s.goal.assumption}</p>
                      </div>
                    )}
                    {s.warnings.map((w) => <p key={w} className="mt-2 text-xs text-warning">{w}</p>)}
                    <p className="mt-2 text-xs text-muted">{s.explanation}</p>
                  </Card>
                ))}
              </div>
              <p className="text-xs text-muted">{result.disclaimer}</p>
            </>
          )}

          <Card>
            <CardHeader title="How much do I need to save?" description="Monthly saving required to reach a goal or target in time" />
            <CardBody className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-3">
                <Field label="Goal" htmlFor="req-goal">
                  <Select id="req-goal" value={reqGoal} onChange={(e) => setReqGoal(e.target.value)}>
                    <option value="">Custom target</option>
                    {activeGoals.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
                  </Select>
                </Field>
                {!reqGoal && <>
                  <Field label={`Target (${currency})`} htmlFor="req-target"><Input id="req-target" inputMode="decimal" value={reqTarget} onChange={(e) => setReqTarget(e.target.value)} placeholder="50000" /></Field>
                  <Field label="Months" htmlFor="req-months"><Input id="req-months" type="number" min={1} max={600} value={reqMonths} onChange={(e) => setReqMonths(e.target.value)} /></Field>
                </>}
              </div>
              <Button onClick={calcRequired}><Target className="h-4 w-4" aria-hidden />Calculate</Button>
              {reqError && <p role="alert" className="text-[13px] text-danger">{reqError}</p>}
              {required && (required.goal_completed ? <p className="text-[13px] text-success">{required.message}</p> : (
                <div className="rounded-lg bg-surface-2 p-3 text-[13px]">
                  <p><strong className="tabular">{money(required.required_monthly_minor)}</strong> per month for {required.months} month(s).</p>
                  {required.required_reduction_pct !== null && required.required_reduction_pct !== undefined
                    ? <p className="mt-1 text-text-2">That is {required.required_reduction_pct}% of your baseline spending ({money(required.baseline_total_minor ?? 0)}/month){required.feasible ? '.' : ' — more than you currently spend, so cutting expenses alone cannot reach it.'}</p>
                    : <p className="mt-1 text-muted">No baseline spending to compare against.</p>}
                </div>
              ))}
            </CardBody>
          </Card>
        </div>
      </div>
    </>
  )
}
