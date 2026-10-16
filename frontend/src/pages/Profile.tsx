import { useState } from 'react'
import { toast } from 'sonner'
import { KeyRound } from 'lucide-react'
import { api, errorMessage, fieldErrors } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAppData } from '../lib/appData'
import { formatTimestampDate } from '../lib/format'
import { useDocumentTitle } from '../lib/hooks'
import { Badge, Button, Card, Field, Input, PageHeader, SettingsSection } from '../components/ui/primitives'

export default function ProfilePage() {
  useDocumentTitle('Profile')
  const { me, reload } = useAppData()
  const { user } = useAuth()
  const [name, setName] = useState(me?.preferences.display_name || me?.user.name || user?.name || '')
  const [saving, setSaving] = useState(false)
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' })
  const [pwErrors, setPwErrors] = useState<Record<string, string>>({})
  const [pwBusy, setPwBusy] = useState(false)

  const saveName = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return toast.error('Name cannot be empty')
    setSaving(true)
    try {
      await api.put('/preferences', { display_name: name.trim() })
      await reload()
      toast.success('Profile updated')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    const errs: Record<string, string> = {}
    if (!pw.current) errs.current_password = 'Enter your current password'
    if (pw.next.length < 8 || !/\d/.test(pw.next) || !/[A-Za-z]/.test(pw.next)) errs.new_password = 'At least 8 characters with a letter and a number'
    if (pw.next !== pw.confirm) errs.confirm = 'Passwords do not match'
    setPwErrors(errs)
    if (Object.keys(errs).length) return
    setPwBusy(true)
    try {
      await api.post('/auth/change-password', { current_password: pw.current, new_password: pw.next })
      setPw({ current: '', next: '', confirm: '' })
      toast.success('Password changed')
    } catch (err) {
      setPwErrors({ ...fieldErrors(err), form: errorMessage(err) })
    } finally {
      setPwBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <PageHeader title="Profile" description="Your account details and sign-in." />
      <Card variant="featured" className="flex flex-wrap items-center gap-4 p-5">
        <div className="brand-gradient flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-xl font-semibold text-white" aria-hidden>
          {(me?.preferences.display_name || me?.user.name || user?.name || 'A').slice(0, 1).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-lg font-semibold">{me?.preferences.display_name || me?.user.name || user?.name}</p>
          <p className="truncate text-[13px] text-muted">{me?.user.email || user?.email}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <Badge tone="primary">{me?.auth_mode === 'cognito' ? 'Amazon Cognito account' : 'Local account'}</Badge>
          <Badge>{me?.preferences.currency} · {me?.preferences.timezone}</Badge>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <SettingsSection title="Personal details" description="Your display name appears in the app. Email is your sign-in identifier.">
          <form onSubmit={saveName} className="max-w-md space-y-4">
            <Field label="Display name" htmlFor="display-name"><Input id="display-name" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} /></Field>
            <Field label="Email" htmlFor="email" hint={me?.auth_mode === 'cognito' ? 'Managed by Amazon Cognito' : 'Email cannot be changed'}>
              <Input id="email" value={me?.user.email || user?.email || ''} disabled readOnly />
            </Field>
            <Button type="submit" loading={saving}>Save</Button>
          </form>
        </SettingsSection>
        {me?.auth_mode === 'local' ? (
          <SettingsSection title="Change password" description="At least 8 characters with a letter and a number.">
            <form onSubmit={changePassword} className="max-w-md space-y-4" noValidate>
              <Field label="Current password" htmlFor="pw-current" error={pwErrors.current_password}><Input id="pw-current" type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} /></Field>
              <Field label="New password" htmlFor="pw-new" error={pwErrors.new_password}><Input id="pw-new" type="password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} /></Field>
              <Field label="Confirm new password" htmlFor="pw-confirm" error={pwErrors.confirm}><Input id="pw-confirm" type="password" autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} /></Field>
              {pwErrors.form && !pwErrors.current_password && !pwErrors.new_password && <p role="alert" className="text-[13px] text-danger">{pwErrors.form}</p>}
              <Button type="submit" loading={pwBusy}><KeyRound className="h-4 w-4" aria-hidden />Change password</Button>
            </form>
          </SettingsSection>
        ) : (
          <SettingsSection title="Password" description="Your password is managed by Amazon Cognito."><p className="text-[13px] text-muted">Use the sign-in page's recovery flow to change it.</p></SettingsSection>
        )}
        <SettingsSection title="Session" description="Sign out from the account card at the bottom of the sidebar (or the navigation menu on mobile).">
          <p className="text-[12.5px] text-muted">Preferences last updated {me ? formatTimestampDate(me.preferences.updated_at, me.preferences.timezone) : '—'}.</p>
        </SettingsSection>
      </Card>
    </div>
  )
}
