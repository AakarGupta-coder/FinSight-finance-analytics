import { useState } from 'react'
import { toast } from 'sonner'
import { Archive, ArchiveRestore, CalendarClock, ListChecks, MinusCircle, Pencil, PiggyBank, Plus, PlusCircle, Trash2 } from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'
import { formatDate, formatTimestampDate, minorToInput, parseMoneyToMinor } from '../lib/format'
import { useApi, useDocumentTitle } from '../lib/hooks'
import type { Goal } from '../lib/types'
import { AnimatedNumber, Badge, Button, Card, EmptyState, ErrorState, Field, Input, PageHeader, Progress, Skeleton, StatCard } from '../components/ui/primitives'
import { ConfirmDialog, Dialog } from '../components/ui/dialog'

const STATUS: Record<Goal['status'], { label: string; tone: 'success' | 'warning' | 'danger' | 'neutral' | 'info' }> = {
  on_track: { label: 'On track', tone: 'success' },
  behind: { label: 'Behind schedule', tone: 'warning' },
  not_started: { label: 'No contributions yet', tone: 'neutral' },
  completed: { label: 'Completed', tone: 'success' },
  overdue: { label: 'Target date passed', tone: 'danger' },
  archived: { label: 'Archived', tone: 'neutral' },
}

function GoalDialog({ goal, onClose, onSaved }: { goal: Goal | null | 'new'; onClose: () => void; onSaved: () => void }) {
  const { currency, today } = useAppData()
  const editing = goal && goal !== 'new' ? goal : null
  const [name, setName] = useState(editing?.name ?? '')
  const [target, setTarget] = useState(editing ? minorToInput(editing.target_minor, currency) : '')
  const [saved, setSaved] = useState('')
  const [date, setDate] = useState(editing?.target_date ?? '')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const errs: Record<string, string> = {}
    const targetMinor = parseMoneyToMinor(target, currency)
    const savedMinor = saved ? parseMoneyToMinor(saved, currency) : 0
    if (!name.trim()) errs.name = 'Enter a goal name'
    if (!targetMinor) errs.target = 'Enter a target greater than zero'
    if (savedMinor === null) errs.saved = 'Enter a valid amount'
    if (date && date <= today && date !== editing?.target_date) errs.date = 'Target date must be in the future'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    try {
      if (editing) {
        await api.put(`/goals/${editing.id}`, { name: name.trim(), target_minor: targetMinor, target_date: date || null, clear_target_date: !date })
        toast.success('Goal updated')
      } else {
        await api.post('/goals', { name: name.trim(), target_minor: targetMinor, saved_minor: savedMinor, target_date: date || null })
        toast.success('Goal created')
      }
      onSaved()
      onClose()
    } catch (err) {
      setErrors({ form: errorMessage(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={!!goal} onOpenChange={(o) => !o && onClose()} title={editing ? 'Edit goal' : 'New savings goal'} size="sm">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Goal name" htmlFor="goal-name" error={errors.name}><Input id="goal-name" value={name} maxLength={80} placeholder="e.g. New laptop" onChange={(e) => setName(e.target.value)} /></Field>
        <Field label={`Target amount (${currency})`} htmlFor="goal-target" error={errors.target}><Input id="goal-target" inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} /></Field>
        {!editing && <Field label={`Already saved (${currency})`} htmlFor="goal-saved" error={errors.saved} hint="Optional starting balance — recorded as an actual contribution">
          <Input id="goal-saved" inputMode="decimal" value={saved} onChange={(e) => setSaved(e.target.value)} placeholder="0" /></Field>}
        <Field label="Target date" htmlFor="goal-date" error={errors.date} hint="Optional — needed to calculate a monthly contribution">
          <Input id="goal-date" type="date" min={today} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        {errors.form && <p role="alert" className="rounded-lg bg-danger-soft px-3 py-2 text-[13px] text-danger">{errors.form}</p>}
        <div className="flex justify-end gap-2"><Button variant="outline" onClick={onClose}>Cancel</Button><Button type="submit" loading={busy}>{editing ? 'Save' : 'Create goal'}</Button></div>
      </form>
    </Dialog>
  )
}

function ContributionDialog({ goal, kind, onClose, onSaved }: { goal: Goal | null; kind: 'add' | 'withdraw'; onClose: () => void; onSaved: () => void }) {
  const { currency, today, money } = useAppData()
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState(today)
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  if (!goal) return null
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const minor = parseMoneyToMinor(amount, currency)
    if (!minor) return setError('Enter an amount greater than zero')
    setBusy(true)
    try {
      await api.post(`/goals/${goal.id}/contributions`, { amount_minor: kind === 'add' ? minor : -minor, date, note: note || null })
      toast.success(kind === 'add' ? `Added ${money(minor)} to ${goal.name}` : `Withdrew ${money(minor)} from ${goal.name}`)
      onSaved()
      onClose()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()} size="sm" title={kind === 'add' ? `Add to “${goal.name}”` : `Withdraw from “${goal.name}”`}
      description="Record money you actually set aside. Regular expenses are never counted as savings.">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label={`Amount (${currency})`} htmlFor="c-amount" error={error ?? undefined}><Input id="c-amount" inputMode="decimal" autoFocus value={amount} onChange={(e) => { setAmount(e.target.value); setError(null) }} /></Field>
        <Field label="Date" htmlFor="c-date"><Input id="c-date" type="date" max={today} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <Field label="Note" htmlFor="c-note" hint="Optional"><Input id="c-note" maxLength={200} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        <div className="flex justify-end gap-2"><Button variant="outline" onClick={onClose}>Cancel</Button><Button type="submit" loading={busy}>{kind === 'add' ? 'Add contribution' : 'Withdraw'}</Button></div>
      </form>
    </Dialog>
  )
}

export default function GoalsPage() {
  useDocumentTitle('Savings goals')
  const { money, timezone } = useAppData()
  const { data, error, reload } = useApi<{ items: Goal[]; summary: { total_target_minor: number; total_saved_minor: number; required_monthly_minor: number; active_count: number; completed_count: number } }>('/goals')
  const [editing, setEditing] = useState<Goal | null | 'new'>(null)
  const [contrib, setContrib] = useState<{ goal: Goal; kind: 'add' | 'withdraw' } | null>(null)
  const [deleting, setDeleting] = useState<Goal | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

  const archive = async (g: Goal) => {
    try {
      await api.put(`/goals/${g.id}`, { archived: !g.archived })
      toast.success(g.archived ? 'Goal restored' : 'Goal archived')
      reload()
    } catch (err) {
      toast.error(errorMessage(err))
    }
  }

  return (
    <>
      <PageHeader title="Savings goals" description="Plan what you're saving for and track actual contributions."
        actions={<Button onClick={() => setEditing('new')}><Plus className="h-4 w-4" aria-hidden />New goal</Button>} />
      {error ? <Card><ErrorState error={error} onRetry={reload} /></Card> : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard emphasis icon={<PiggyBank />} label="Saved across goals" loading={!data} value={money(data?.summary.total_saved_minor ?? 0)} sub={data && `of ${money(data.summary.total_target_minor)} targeted`} />
            <StatCard icon={<CalendarClock />} label="Planned monthly saving" loading={!data} value={money(data?.summary.required_monthly_minor ?? 0, { round: true })} sub="Required to meet all target dates (hypothetical)" />
            <StatCard icon={<ListChecks />} label="Goals" loading={!data} value={`${data?.summary.active_count ?? 0} active`} sub={data && `${data.summary.completed_count} completed`} />
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {!data ? [0, 1].map((i) => <Skeleton key={i} className="h-48" />) : data.items.length === 0 ? (
              <Card className="lg:col-span-2"><EmptyState icon={<PiggyBank className="h-5 w-5" />} title="No savings goals yet"
                description="Use New goal above to plan an emergency fund or a new laptop and see how much to save each month." /></Card>
            ) : data.items.map((g) => {
              const st = STATUS[g.status]
              return (
                <Card key={g.id} className={g.archived ? 'p-5 opacity-70' : 'p-5'}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2"><h2 className="text-[15px] font-semibold">{g.name}</h2>
                        {/* Keyed by status so a change (e.g. reaching the target) is acknowledged with a brief pop. */}
                        <span key={g.status} className="fs-pop-in inline-flex"><Badge tone={st.tone}>{st.label}</Badge></span>{g.is_demo && <Badge>Demo</Badge>}</div>
                      <p className="mt-0.5 text-xs text-muted">{g.target_date ? `Target ${formatDate(g.target_date)}` : 'No target date'} · created {formatTimestampDate(g.created_at, timezone)}</p>
                    </div>
                    <div className="flex">
                      <Button variant="ghost" size="icon" aria-label={`Edit ${g.name}`} onClick={() => setEditing(g)}><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" aria-label={g.archived ? `Restore ${g.name}` : `Archive ${g.name}`} onClick={() => archive(g)}>{g.archived ? <ArchiveRestore className="h-4 w-4" /> : <Archive className="h-4 w-4" />}</Button>
                      <Button variant="ghost" size="icon" aria-label={`Delete ${g.name}`} onClick={() => setDeleting(g)}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </div>
                  <div className="mt-4 flex items-baseline justify-between">
                    <span className="text-xl font-semibold tabular"><AnimatedNumber value={g.saved_minor} format={(v) => money(v)} /></span>
                    <span className="text-[13px] text-muted tabular">of {money(g.target_minor)} · {g.progress_pct}%</span>
                  </div>
                  <Progress className="mt-2" value={g.progress_pct} tone={g.completed ? 'success' : g.status === 'behind' || g.status === 'overdue' ? 'warning' : 'primary'} label={`${g.name} progress`} />
                  <dl className="mt-4 grid grid-cols-2 gap-3 text-[13px] sm:grid-cols-3">
                    <div><dt className="text-xs text-muted">Remaining</dt><dd className="font-medium tabular">{money(g.remaining_minor)}</dd></div>
                    <div><dt className="text-xs text-muted">Needed per month</dt><dd className="font-medium tabular">{g.required_monthly_minor !== null ? money(g.required_monthly_minor, { round: true }) : '—'}</dd></div>
                    <div><dt className="text-xs text-muted">Your recent pace</dt><dd className="font-medium tabular">{money(g.recent_monthly_contribution_minor, { round: true })}/mo</dd></div>
                  </dl>
                  {g.projected_completion_date && !g.completed && <p className="mt-2 text-xs text-muted">At your recent pace you'd reach this around {formatDate(g.projected_completion_date)} (projection).</p>}
                  {!g.archived && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button size="sm" variant="secondary" onClick={() => setContrib({ goal: g, kind: 'add' })}><PlusCircle className="h-3.5 w-3.5" aria-hidden />Add contribution</Button>
                      <Button size="sm" variant="outline" disabled={g.saved_minor <= 0} onClick={() => setContrib({ goal: g, kind: 'withdraw' })}><MinusCircle className="h-3.5 w-3.5" aria-hidden />Withdraw</Button>
                      <Button size="sm" variant="ghost" onClick={() => setExpanded(expanded === g.id ? null : g.id)} aria-expanded={expanded === g.id}>History ({g.contributions.length})</Button>
                    </div>
                  )}
                  {expanded === g.id && (
                    <ul className="mt-3 divide-y divide-border rounded-lg border border-border text-[13px]">
                      {g.contributions.length === 0 ? <li className="p-3 text-muted">No contributions yet.</li> : g.contributions.map((c) => (
                        <li key={c.id} className="flex items-center justify-between gap-2 px-3 py-2">
                          <span>{formatDate(c.date)}{c.note ? <span className="text-muted"> · {c.note}</span> : null}</span>
                          <span className="flex items-center gap-1">
                            <span className={`tabular font-medium ${c.amount_minor < 0 ? 'text-danger' : 'text-success'}`}>{c.amount_minor > 0 ? '+' : ''}{money(c.amount_minor)}</span>
                            <Button variant="ghost" size="icon" className="h-7 w-7" aria-label="Remove entry" onClick={async () => {
                              try { await api.del(`/goals/${g.id}/contributions/${c.id}`); toast.success('Entry removed'); reload() } catch (err) { toast.error(errorMessage(err)) }
                            }}><Trash2 className="h-3.5 w-3.5" /></Button>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>
              )
            })}
          </div>
        </>
      )}
      {editing && <GoalDialog key={editing === 'new' ? 'new' : editing.id} goal={editing} onClose={() => setEditing(null)} onSaved={reload} />}
      {contrib && <ContributionDialog goal={contrib.goal} kind={contrib.kind} onClose={() => setContrib(null)} onSaved={reload} />}
      <ConfirmDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)} title={`Delete “${deleting?.name}”?`}
        description="The goal and its contribution history are permanently deleted. Consider archiving instead."
        onConfirm={async () => {
          try { await api.del(`/goals/${deleting!.id}`); toast.success('Goal deleted'); reload() } catch (err) { toast.error(errorMessage(err)); throw err }
        }} />
    </>
  )
}
