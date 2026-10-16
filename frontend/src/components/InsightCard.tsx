import { useState } from 'react'
import { Link } from 'react-router'
import { AlertOctagon, AlertTriangle, CheckCircle2, ChevronDown, Info, Lightbulb } from 'lucide-react'
import { useAppData } from '../lib/appData'
import { formatDate } from '../lib/format'
import { cn } from '../lib/utils'
import type { Insight } from '../lib/types'
import { Badge } from './ui/primitives'

const KIND: Record<Insight['kind'], { label: string; tone: 'neutral' | 'info' | 'warning' | 'primary' }> = {
  fact: { label: 'Observed fact', tone: 'neutral' },
  estimate: { label: 'Estimate', tone: 'info' },
  projection: { label: 'Projection', tone: 'warning' },
  recommendation: { label: 'Recommendation', tone: 'primary' },
  data_gap: { label: 'More data needed', tone: 'neutral' },
}

const SEVERITY = {
  critical: { icon: AlertOctagon, cls: 'text-danger bg-danger-soft', label: 'Critical' },
  warning: { icon: AlertTriangle, cls: 'text-warning bg-warning-soft', label: 'Needs attention' },
  info: { icon: Info, cls: 'text-info bg-info-soft', label: 'Information' },
  positive: { icon: CheckCircle2, cls: 'text-success bg-success-soft', label: 'Positive' },
}

const ACCENT: Record<Insight['severity'], string> = {
  critical: 'bg-danger', warning: 'bg-warning', info: 'bg-info/70', positive: 'bg-success',
}

function formatValue(key: string, value: unknown, money: (m: number) => string): string | null {
  if (value === null || value === undefined || typeof value === 'object') return null
  if (typeof value === 'number' && key.endsWith('_minor')) return money(value)
  if (typeof value === 'number' && key.endsWith('_pct')) return `${value}%`
  return String(value)
}

const LABELS: Record<string, string> = {
  current_minor: 'Current', previous_minor: 'Previous', change_pct: 'Change', category_minor: 'Category total',
  total_minor: 'Total', share_pct: 'Share', days: 'Days', average_daily_minor: 'Daily average', average_minor: 'Average',
  spent_minor: 'Spent', budget_minor: 'Budget', days_elapsed: 'Days elapsed', days_in_month: 'Days in month',
  projected_minor: 'Projected', remaining_minor: 'Remaining', remaining_days: 'Days left', allowance_minor: 'Daily allowance',
  monthly_total_minor: 'Per month', required_monthly_minor: 'Required per month', recent_monthly_minor: 'Recent per month',
  monthly_base_minor: 'Monthly base', monthly_saving_minor: 'Monthly saving', annual_saving_minor: 'Annual saving',
  saved_minor: 'Saved', target_minor: 'Target', months_with_data: 'Months with data', occurrences: 'Occurrences',
  typical_amount_minor: 'Typical amount', category_before_minor: 'Before', category_after_minor: 'After',
}

export function InsightCard({ insight, compact = false }: { insight: Insight; compact?: boolean }) {
  const { money } = useAppData()
  const [open, setOpen] = useState(false)
  const sev = SEVERITY[insight.severity]
  const kind = KIND[insight.kind]
  const Icon = insight.kind === 'recommendation' ? Lightbulb : sev.icon
  const values = Object.entries(insight.evidence.values)
    .map(([k, v]) => [LABELS[k] ?? k.replace(/_/g, ' '), formatValue(k, v, money)] as const)
    .filter(([, v]) => v !== null)
  const hasEvidence = !!(insight.evidence.calculation || values.length || insight.evidence.transactions.length || insight.evidence.period)

  return (
    // Severity is shown by icon + label; the left accent only reinforces it.
    <article className={cn('fs-lift relative overflow-hidden rounded-xl border border-border transition-colors duration-200 hover:border-border-strong',
      compact ? 'bg-surface-2 p-3 pl-3.5' : 'bg-surface p-4 pl-5 shadow-card')}>
      <span aria-hidden className={cn('absolute inset-y-0 left-0 w-[3px]', ACCENT[insight.severity])} />
      <div className="flex gap-3">
        <div className={cn('flex shrink-0 items-center justify-center rounded-lg', compact ? 'h-7 w-7' : 'h-8 w-8', sev.cls)}>
          <Icon className="h-4 w-4" aria-hidden /><span className="sr-only">{sev.label}</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className={cn('font-medium text-text', compact ? 'text-[13px]' : 'text-sm')}>{insight.title}</h3>
            <Badge tone={kind.tone}>{kind.label}</Badge>
          </div>
          <p className={cn('mt-1 leading-relaxed text-text-2', compact ? 'line-clamp-3 text-[12px]' : 'text-[13px]')}>{insight.message}</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            {hasEvidence && !compact && (
              <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open}
                className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline">
                Why am I seeing this? <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} aria-hidden />
              </button>
            )}
            {insight.action && <Link to={insight.action.href.startsWith('/app') ? insight.action.href : `/app${insight.action.href}`}
              className="text-xs font-medium text-accent hover:underline">{insight.action.label} →</Link>}
          </div>
          {open && (
            <div className="mt-3 space-y-3 rounded-lg border border-border bg-surface-2 p-3 text-xs">
              {insight.evidence.period && <p><span className="text-muted">Period: </span><span className="font-medium">{insight.evidence.period.label}</span></p>}
              {insight.evidence.calculation && <p><span className="text-muted">Calculation: </span><code className="font-medium">{insight.evidence.calculation}</code></p>}
              {values.length > 0 && (
                <dl className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
                  {values.map(([k, v]) => <div key={k}><dt className="text-muted capitalize">{k}</dt><dd className="font-medium tabular">{v}</dd></div>)}
                </dl>
              )}
              {insight.evidence.transactions.length > 0 && (
                <div>
                  <p className="mb-1 text-muted">Supporting transactions</p>
                  <ul className="divide-y divide-border">
                    {insight.evidence.transactions.map((t) => (
                      <li key={t.id} className="flex justify-between gap-3 py-1">
                        <span className="truncate">{formatDate(t.date)} · {t.description}</span>
                        <span className="shrink-0 font-medium tabular">{money(t.amount_minor)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
