import { useState } from 'react'
import { toast } from 'sonner'
import { Database, Plus, Trash2, X } from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAppData } from '../lib/appData'
import { useDocumentTitle } from '../lib/hooks'
import { applyTheme, getTheme, type Theme } from '../lib/utils'
import { Badge, Button, Card, Field, Input, PageHeader, Segmented, Select, SettingsSection } from '../components/ui/primitives'
import { ConfirmDialog, Dialog } from '../components/ui/dialog'
import { AboutAuthorLink } from '../components/AboutAuthor'

const TIMEZONES = ['Asia/Kolkata', 'UTC', 'Asia/Dubai', 'Asia/Singapore', 'Asia/Tokyo', 'Europe/London', 'Europe/Berlin', 'America/New_York', 'America/Chicago', 'America/Los_Angeles', 'Australia/Sydney']

export default function SettingsPage() {
  useDocumentTitle('Settings')
  const { me, reference, reload } = useAppData()
  const { logout } = useAuth()
  const prefs = me!.preferences
  const [currency, setCurrency] = useState(prefs.currency)
  const [timezone, setTimezone] = useState(prefs.timezone)
  const [thresholds, setThresholds] = useState<number[]>(prefs.budget_thresholds)
  const [newThreshold, setNewThreshold] = useState('')
  const [sensitivity, setSensitivity] = useState(prefs.anomaly_sensitivity)
  const [saving, setSaving] = useState(false)
  const [theme, setTheme] = useState<Theme>(getTheme())
  const [categoryName, setCategoryName] = useState('')
  const [removingCat, setRemovingCat] = useState<{ id: string; name: string } | null>(null)
  const [demoBusy, setDemoBusy] = useState<'load' | 'clear' | null>(null)
  const [confirmClearDemo, setConfirmClearDemo] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteText, setDeleteText] = useState('')
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const dirty = currency !== prefs.currency || timezone !== prefs.timezone || sensitivity !== prefs.anomaly_sensitivity
    || JSON.stringify(thresholds) !== JSON.stringify(prefs.budget_thresholds)
  const tzOptions = TIMEZONES.includes(prefs.timezone) ? TIMEZONES : [prefs.timezone, ...TIMEZONES]

  const save = async () => {
    if (!thresholds.length) return toast.error('Keep at least one alert threshold')
    setSaving(true)
    try {
      await api.put('/preferences', { currency, timezone, budget_thresholds: thresholds, anomaly_sensitivity: sensitivity })
      await reload()
      toast.success('Settings saved')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const addThreshold = () => {
    const n = Number(newThreshold)
    if (!Number.isInteger(n) || n < 1 || n > 200) return toast.error('Thresholds are whole percentages from 1 to 200')
    if (thresholds.includes(n)) return toast.error('That threshold already exists')
    if (thresholds.length >= 5) return toast.error('Up to 5 thresholds')
    setThresholds([...thresholds, n].sort((a, b) => a - b))
    setNewThreshold('')
  }

  const addCategory = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!categoryName.trim()) return
    try {
      await api.post('/categories', { name: categoryName.trim() })
      setCategoryName('')
      await reload()
      toast.success('Category added')
    } catch (err) {
      toast.error(errorMessage(err))
    }
  }

  const demo = async (action: 'load' | 'clear') => {
    setDemoBusy(action)
    try {
      if (action === 'load') {
        const r = await api.post<{ created: { expenses: number } }>('/demo-data')
        toast.success(`Loaded ${r.created.expenses} demo transactions`, { description: 'All demo records are labelled “Demo”.' })
      } else {
        const r = await api.del<{ removed: { expenses: number } }>('/demo-data')
        toast.success(`Removed ${r.removed.expenses} demo transactions`)
      }
      await reload()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setDemoBusy(null)
    }
  }

  const deleteAll = async () => {
    setDeleteBusy(true)
    setDeleteError(null)
    try {
      const r = await api.post<{ account_deleted: boolean }>('/account/delete-data', { confirm: 'DELETE', password: deletePassword || null })
      setDeleteOpen(false)
      toast.success(r.account_deleted ? 'Account and data deleted' : 'All data deleted')
      if (r.account_deleted) logout()
      else await reload()
    } catch (err) {
      setDeleteError(errorMessage(err))
    } finally {
      setDeleteBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <PageHeader title="Settings" description="Preferences for currency, alerts, categories, appearance and your data." />

      <Card className="overflow-hidden">
        <div className="border-b border-border bg-surface-2 px-5 py-2.5"><h2 className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">Preferences</h2></div>
        <SettingsSection title="Regional" description="Changing currency relabels amounts; it does not convert existing records.">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Currency" htmlFor="currency">
              <Select id="currency" value={currency} onChange={(e) => setCurrency(e.target.value)}>
                {reference?.currencies.map((c) => <option key={c.code} value={c.code}>{c.code} ({c.symbol.trim()})</option>)}
              </Select>
            </Field>
            <Field label="Timezone" htmlFor="timezone" hint="Used to decide what “today” and “this month” mean">
              <Select id="timezone" value={timezone} onChange={(e) => setTimezone(e.target.value)}>
                {tzOptions.map((t) => <option key={t} value={t}>{t}</option>)}
              </Select>
            </Field>
          </div>
        </SettingsSection>
        <SettingsSection title="Budget alerts" description="You get one alert per threshold, per budget, each month.">
          <div className="flex flex-wrap items-center gap-2">
            {thresholds.map((t) => (
              <Badge key={t} tone="primary">{t}%
                <button type="button" aria-label={`Remove ${t}% threshold`} className="ml-0.5 rounded hover:opacity-70" onClick={() => setThresholds(thresholds.filter((x) => x !== t))}><X className="h-3 w-3" /></button>
              </Badge>
            ))}
            <div className="flex items-center gap-1.5">
              <Input aria-label="New threshold percentage" className="h-8 w-20" inputMode="numeric" placeholder="e.g. 50" value={newThreshold}
                onChange={(e) => setNewThreshold(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addThreshold() } }} />
              <Button size="sm" variant="outline" onClick={addThreshold}><Plus className="h-3.5 w-3.5" aria-hidden />Add</Button>
            </div>
          </div>
        </SettingsSection>
        <SettingsSection title="Anomaly sensitivity" description="Higher sensitivity flags more transactions; lower sensitivity reduces false positives.">
          <Segmented label="Sensitivity" value={sensitivity} onChange={setSensitivity} options={[
            { value: 'conservative', label: 'Conservative' }, { value: 'balanced', label: 'Balanced' }, { value: 'sensitive', label: 'Sensitive' }]} />
        </SettingsSection>
        <div className="sticky bottom-0 z-10 flex items-center justify-end gap-3 border-t border-border bg-surface/95 px-5 py-3 backdrop-blur">
          {dirty && <span className="text-xs text-muted">You have unsaved changes</span>}
          <Button onClick={save} loading={saving} disabled={!dirty}>Save preferences</Button>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="border-b border-border bg-surface-2 px-5 py-2.5"><h2 className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">Workspace</h2></div>
        <SettingsSection title="Appearance" description="Dark is the default. The header toggle switches dark/light; “Match system” follows your OS. Saved in this browser only.">
          <Segmented label="Theme" value={theme} onChange={(t) => { setTheme(t); applyTheme(t) }} options={[
            { value: 'dark', label: 'Dark' }, { value: 'light', label: 'Light' }, { value: 'system', label: 'Match system' }]} />
        </SettingsSection>
        <SettingsSection title="Categories" description="Built-in categories cannot be removed. Removing a custom category moves its expenses to Other.">
          <div className="flex flex-wrap gap-2">
            {reference?.categories.map((c) => (
              <Badge key={c.id} tone={c.custom ? 'primary' : 'neutral'}>{c.name}
                {c.custom && <button type="button" aria-label={`Remove ${c.name}`} className="ml-0.5 rounded hover:opacity-70" onClick={() => setRemovingCat(c)}><X className="h-3 w-3" /></button>}
              </Badge>
            ))}
          </div>
          <form onSubmit={addCategory} className="mt-4 flex flex-wrap gap-2">
            <Input aria-label="New category name" placeholder="New category, e.g. Pets" maxLength={40} value={categoryName} onChange={(e) => setCategoryName(e.target.value)} className="max-w-xs" />
            <Button type="submit" variant="outline" disabled={!categoryName.trim()}><Plus className="h-4 w-4" aria-hidden />Add category</Button>
          </form>
        </SettingsSection>
        {me?.demo_data_enabled && (
          <SettingsSection title="Demo data" description="Synthetic sample data for exploring features. Every demo record is labelled and can be removed in one step.">
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" loading={demoBusy === 'load'} onClick={() => demo('load')}><Database className="h-4 w-4" aria-hidden />Load demo data</Button>
              <Button variant="ghost" loading={demoBusy === 'clear'} onClick={() => setConfirmClearDemo(true)}><Trash2 className="h-4 w-4" aria-hidden />Remove demo data</Button>
            </div>
          </SettingsSection>
        )}
      </Card>

      <Card className="overflow-hidden">
        <SettingsSection title="About" description="FinSight — Cloud-Based Personal Finance Intelligence & Expense Analytics Platform.">
          <p className="text-[13px] text-text-2">Created by <AboutAuthorLink>Aakar Gupta</AboutAuthorLink></p>
        </SettingsSection>
      </Card>

      <Card className="overflow-hidden border-danger/30">
        <SettingsSection danger title="Delete all data" description={me?.auth_mode === 'local' ? 'Permanently deletes your account, transactions, budgets, goals, alerts and receipts.' : 'Permanently deletes all transactions, budgets, goals, alerts and receipts.'}>
          <Button variant="danger" onClick={() => { setDeleteOpen(true); setDeleteText(''); setDeletePassword(''); setDeleteError(null) }}><Trash2 className="h-4 w-4" aria-hidden />Delete everything</Button>
        </SettingsSection>
      </Card>

      <ConfirmDialog open={!!removingCat} onOpenChange={(o) => !o && setRemovingCat(null)} title={`Remove “${removingCat?.name}”?`}
        description="Expenses in this category move to Other, and its budget is removed." confirmLabel="Remove category"
        onConfirm={async () => {
          try {
            const r = await api.del<{ moved_to_other: number }>(`/categories/${removingCat!.id}`)
            await reload()
            toast.success(`Category removed${r.moved_to_other ? ` · ${r.moved_to_other} expense(s) moved to Other` : ''}`)
          } catch (err) { toast.error(errorMessage(err)); throw err }
        }} />
      <ConfirmDialog open={confirmClearDemo} onOpenChange={setConfirmClearDemo} title="Remove demo data?" description="All records labelled Demo are deleted. Your own records are kept." confirmLabel="Remove demo data"
        onConfirm={() => demo('clear')} />
      <Dialog open={deleteOpen} onOpenChange={(o) => !deleteBusy && setDeleteOpen(o)} title="Delete all data permanently?" size="sm"
        description="This cannot be undone. Export your transactions first if you want a copy."
        footer={<><Button variant="outline" onClick={() => setDeleteOpen(false)} disabled={deleteBusy}>Cancel</Button>
          <Button variant="danger" loading={deleteBusy} disabled={deleteText !== 'DELETE' || (me?.auth_mode === 'local' && !deletePassword)} onClick={deleteAll}>Delete permanently</Button></>}>
        <div className="space-y-3">
          <Field label='Type "DELETE" to confirm' htmlFor="delete-confirm"><Input id="delete-confirm" value={deleteText} onChange={(e) => setDeleteText(e.target.value)} autoComplete="off" /></Field>
          {me?.auth_mode === 'local' && <Field label="Password" htmlFor="delete-password"><Input id="delete-password" type="password" autoComplete="current-password" value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} /></Field>}
          {deleteError && <p role="alert" className="text-[13px] text-danger">{deleteError}</p>}
        </div>
      </Dialog>
    </div>
  )
}
