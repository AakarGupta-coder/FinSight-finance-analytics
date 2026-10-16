import { toast } from 'sonner'
import { money } from '../lib/format'
import type { BudgetAlert } from '../lib/types'

/** Toasts for side effects reported by the API after an expense change. */
export function announceMutationEffects(result: { new_anomalies?: number; budget_alerts?: BudgetAlert[] }, currency: string) {
  const alerts = result.budget_alerts ?? []
  // Report only the highest newly crossed threshold per budget.
  const highest = new Map<string, BudgetAlert>()
  alerts.forEach((a) => {
    const cur = highest.get(a.category_name)
    if (!cur || a.threshold > cur.threshold) highest.set(a.category_name, a)
  })
  highest.forEach((a) => {
    const text = `${a.category_name} budget: ${a.threshold}% reached (${money(a.spent_minor, currency)} of ${money(a.budget_minor, currency)})`
    if (a.threshold >= 100) toast.error(text)
    else toast.warning(text)
  })
  if (result.new_anomalies) {
    toast.info(`${result.new_anomalies} transaction(s) flagged for review`, { description: 'See Anomaly alerts for details.' })
  }
}
