import { useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { AlertOctagon, CheckCheck, Eye, Pencil, RefreshCw, RotateCcw, ShieldAlert, ShieldCheck, XCircle } from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'
import { formatDate, formatDateTime } from '../lib/format'
import { useApi, useDocumentTitle } from '../lib/hooks'
import type { AnomalyAlert } from '../lib/types'
import { Badge, Button, Card, EmptyState, ErrorState, PageHeader, Segmented, Skeleton, StatCard } from '../components/ui/primitives'
import { cn } from '../lib/utils'

type StatusFilter = 'open' | 'reviewed' | 'legitimate' | 'dismissed' | 'all'

const RULES: Record<AnomalyAlert['rule'], string> = {
  category_outlier: 'Unusual for category',
  overall_outlier: 'Unusually large',
  duplicate: 'Possible duplicate',
  repeated_similar: 'Repeated transactions',
  category_spike: 'Category spending spike',
}
const SEVERITY_TONE = { high: 'danger', medium: 'warning', low: 'info' } as const
const STATUS_LABEL = { open: 'Needs review', reviewed: 'Reviewed', legitimate: 'Confirmed legitimate', dismissed: 'Dismissed' }

function Comparison({ alert }: { alert: AnomalyAlert }) {
  const { money } = useAppData()
  const c = alert.comparison as Record<string, any>
  const items: [string, string][] = []
  if (c.median_minor !== undefined) items.push(['Typical (median)', money(Math.round(c.median_minor))])
  if (c.ratio !== undefined) items.push(['Times typical', `${c.ratio}×`])
  if (c.p90_minor !== undefined) items.push(['90th percentile', money(c.p90_minor)])
  if (c.p95_minor !== undefined) items.push(['95th percentile', money(c.p95_minor)])
  if (c.robust_z !== undefined && c.robust_z !== null) items.push(['Robust z-score', String(c.robust_z)])
  if (c.sample_size !== undefined) items.push(['Compared with', `${c.sample_size} transaction(s)`])
  if (c.month_total_minor !== undefined) items.push(['Month total', money(c.month_total_minor)])
  if (c.average_minor !== undefined) items.push(['Monthly average', money(c.average_minor)])
  if (c.count !== undefined) items.push(['Transactions', String(c.count)])
  if (c.window_days !== undefined) items.push(['Matched within', `${c.window_days} day`])
  if (!items.length) return null
  return (
    <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 rounded-xl border border-border bg-surface-2 p-3 text-xs sm:grid-cols-3 lg:grid-cols-6">
      {items.map(([k, v]) => <div key={k}><dt className="text-muted">{k}</dt><dd className="font-medium tabular">{v}</dd></div>)}
      {c.method && <div className="col-span-full text-muted">Method: {c.method}</div>}
    </dl>
  )
}

export default function AnomaliesPage() {
  useDocumentTitle('Anomaly alerts')
  const { money, timezone } = useAppData()
  const navigate = useNavigate()
  const [status, setStatus] = useState<StatusFilter>('open')
  const { data, error, reload } = useApi<{ items: AnomalyAlert[]; counts: Record<string, number>; sensitivity: string }>('/anomalies', { status })
  const [busy, setBusy] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)

  const act = async (alert: AnomalyAlert, action: 'reviewed' | 'legitimate' | 'dismissed' | 'open') => {
    setBusy(alert.id + action)
    try {
      await api.post(`/anomalies/${alert.id}/review`, { action })
      toast.success({ reviewed: 'Marked as reviewed', legitimate: 'Confirmed as legitimate', dismissed: 'Alert dismissed', open: 'Alert reopened' }[action])
      reload()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const scan = async () => {
    setScanning(true)
    try {
      const r = await api.post<{ scanned: number; created: number }>('/anomalies/scan')
      toast.success(`Scanned ${r.scanned} transaction(s)`, { description: r.created ? `${r.created} new alert(s)` : 'No new alerts' })
      reload()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setScanning(false)
    }
  }

  const count = (k: string) => data?.counts[k] ?? 0
  return (
    <>
      <PageHeader title="Anomaly alerts"
        description="Transactions that look unusual compared with your own history. An alert means “worth a look” — not that anything is wrong."
        actions={<Button variant="outline" onClick={scan} loading={scanning}><RefreshCw className="h-4 w-4" aria-hidden />Re-scan last 180 days</Button>} />

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatCard emphasis icon={<ShieldAlert className="h-[18px] w-[18px]" />} label="Needs review" loading={!data && !error} value={count('open')} sub="Open alerts across all transactions" />
        <StatCard icon={<CheckCheck className="h-[18px] w-[18px]" />} label="Confirmed legitimate" loading={!data && !error} value={count('legitimate')} sub="Marked as expected spending" />
        <StatCard icon={<AlertOctagon className="h-[18px] w-[18px]" />} label="Reviewed or dismissed" loading={!data && !error} value={count('reviewed') + count('dismissed')} sub={data ? `Sensitivity: ${data.sensitivity}` : undefined} />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3"><Segmented label="Alert status" size="sm" value={status} onChange={setStatus} options={[
          { value: 'open', label: `Needs review (${count('open')})` }, { value: 'reviewed', label: `Reviewed (${count('reviewed')})` },
          { value: 'legitimate', label: `Legitimate (${count('legitimate')})` }, { value: 'dismissed', label: `Dismissed (${count('dismissed')})` },
          { value: 'all', label: 'All' }]} />
        {data && <span className="text-xs text-muted">Sensitivity: {data.sensitivity} (change in Settings)</span>}
      </div>

      {error ? <Card><ErrorState error={error} onRetry={reload} /></Card> : !data ? (
        <div className="space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-36" />)}</div>
      ) : data.items.length === 0 ? (
        <Card><EmptyState icon={status === 'open' ? <ShieldCheck className="h-5 w-5" /> : <ShieldAlert className="h-5 w-5" />}
          title={status === 'open' ? 'Nothing needs review' : 'No alerts in this view'}
          description="Detection runs automatically whenever you add or edit a transaction. Small categories need at least 5 past transactions before amounts are compared." /></Card>
      ) : (
        <ul className="space-y-3">
          {data.items.map((a) => (
            <li key={a.id}>
              <Card className="relative overflow-hidden p-4 pl-5">
                <span aria-hidden className={cn('absolute inset-y-0 left-0 w-1', { high: 'bg-danger', medium: 'bg-warning-fill', low: 'bg-info' }[a.severity])} />
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={SEVERITY_TONE[a.severity]}>{a.severity} severity</Badge>
                      <Badge>{RULES[a.rule]}</Badge>
                      <Badge tone={a.status === 'open' ? 'warning' : 'neutral'}>{STATUS_LABEL[a.status]}</Badge>
                      {a.is_demo && <Badge>Demo</Badge>}
                    </div>
                    {a.expense ? (
                      <p className="mt-2 text-sm font-semibold">{a.expense.description}
                        <span className="font-normal text-muted"> · {formatDate(a.expense.date)} · {a.expense.category_name}{a.expense.merchant ? ` · ${a.expense.merchant}` : ''}</span></p>
                    ) : <p className="mt-2 text-sm text-muted">The related transaction no longer exists.</p>}
                    <p className="mt-1 text-[13px] text-text-2">{a.reason}</p>
                  </div>
                  {a.expense && <p className="shrink-0 text-lg font-semibold tabular">{money(a.expense.amount_minor)}</p>}
                </div>
                <Comparison alert={a} />
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs text-muted">Detected {formatDateTime(a.detected_at, timezone)}{a.status_updated_at && a.status !== 'open' ? ` · updated ${formatDateTime(a.status_updated_at, timezone)}` : ''}</p>
                  <div className="flex flex-wrap gap-2">
                    {a.status === 'open' ? <>
                      <Button size="sm" variant="outline" loading={busy === a.id + 'reviewed'} onClick={() => act(a, 'reviewed')}><Eye className="h-3.5 w-3.5" aria-hidden />Mark reviewed</Button>
                      <Button size="sm" variant="outline" loading={busy === a.id + 'legitimate'} onClick={() => act(a, 'legitimate')}><CheckCheck className="h-3.5 w-3.5" aria-hidden />It's legitimate</Button>
                      <Button size="sm" variant="ghost" loading={busy === a.id + 'dismissed'} onClick={() => act(a, 'dismissed')}><XCircle className="h-3.5 w-3.5" aria-hidden />Dismiss</Button>
                    </> : <Button size="sm" variant="ghost" loading={busy === a.id + 'open'} onClick={() => act(a, 'open')}><RotateCcw className="h-3.5 w-3.5" aria-hidden />Reopen</Button>}
                    {a.expense && <Button size="sm" variant="secondary" onClick={() => navigate(`/app/transactions/${a.expense!.id}/edit`)}><Pencil className="h-3.5 w-3.5" aria-hidden />Correct transaction</Button>}
                  </div>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
