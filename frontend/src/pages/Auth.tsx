import { useState, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useLocation, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { useAuth } from '../lib/auth'
import { errorMessage, fieldErrors } from '../lib/api'
import { useDocumentTitle } from '../lib/hooks'
import { Button, Field, Input } from '../components/ui/primitives'
import { BRAND, BrandLogo } from '../components/brand/Brand'

function AuthLayout({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer: ReactNode }) {
  return (
    <div className="canvas-glow relative isolate flex min-h-full items-center justify-center px-4 py-12">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute left-1/2 top-[-8rem] h-80 w-[36rem] -translate-x-1/2 rounded-full bg-emerald/10 blur-3xl" />
      </div>
      <div className="page-enter w-full max-w-sm">
        <div className="mb-7 flex flex-col items-center text-center">
          <Link to="/" aria-label="FinSight home" className="rounded-lg"><BrandLogo size="lg" /></Link>
          <p className="mt-2 max-w-xs text-[13px] text-muted">{BRAND.tagline}</p>
        </div>
        {/* Forms stay on a solid surface for readability. */}
        <div className="ambient-top edge-highlight rounded-2xl border border-border p-6 sm:p-7">
          <h1 className="text-lg font-semibold">{title}</h1>
          <p className="mt-1 text-[13px] text-muted">{subtitle}</p>
          <div className="mt-5">{children}</div>
        </div>
        <p className="mt-5 text-center text-[13px] text-muted">{footer}</p>
      </div>
    </div>
  )
}

const loginSchema = z.object({
  email: z.string().trim().email('Enter a valid email address'),
  password: z.string().min(1, 'Enter your password'),
})

export function LoginPage() {
  useDocumentTitle('Sign in')
  const { login, sessionMessage } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof loginSchema>>({ resolver: zodResolver(loginSchema) })

  const onSubmit = handleSubmit(async (values) => {
    setError(null)
    try {
      await login(values.email, values.password)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from && from.startsWith('/app') ? from : '/app', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    }
  })

  return (
    <AuthLayout title="Sign in" subtitle="Welcome back. Sign in to view your finances."
      footer={<>New here? <Link to="/register" className="font-medium text-primary hover:underline">Create an account</Link></>}>
      {sessionMessage && <p className="mb-4 rounded-lg bg-info-soft px-3 py-2 text-[13px] text-info">{sessionMessage}</p>}
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label="Email" htmlFor="email" error={errors.email?.message}>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} {...register('email')} />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password?.message}>
          <Input id="password" type="password" autoComplete="current-password" aria-invalid={!!errors.password} {...register('password')} />
        </Field>
        {error && <p role="alert" className="rounded-lg bg-danger-soft px-3 py-2 text-[13px] text-danger">{error}</p>}
        <Button type="submit" className="w-full justify-center" loading={isSubmitting}>Sign in</Button>
      </form>
    </AuthLayout>
  )
}

const registerSchema = z.object({
  name: z.string().trim().min(1, 'Enter your name').max(80),
  email: z.string().trim().email('Enter a valid email address'),
  password: z.string().min(8, 'At least 8 characters').max(128)
    .regex(/[A-Za-z]/, 'Include at least one letter').regex(/\d/, 'Include at least one number'),
  confirm: z.string(),
}).refine((v) => v.password === v.confirm, { path: ['confirm'], message: 'Passwords do not match' })

export function RegisterPage() {
  useDocumentTitle('Create account')
  const { register: signUp, confirmSignUp, resendCode, login, config } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<{ email: string; password: string } | null>(null)
  const [code, setCode] = useState('')
  const [confirming, setConfirming] = useState(false)
  const { register, handleSubmit, setError: setFieldError, formState: { errors, isSubmitting } } =
    useForm<z.infer<typeof registerSchema>>({ resolver: zodResolver(registerSchema) })

  const onSubmit = handleSubmit(async (values) => {
    setError(null)
    try {
      const result = await signUp(values.name, values.email, values.password)
      if (result === 'confirm_required') {
        setPending({ email: values.email, password: values.password })
        return
      }
      toast.success('Account created')
      navigate('/app', { replace: true })
    } catch (err) {
      const fields = fieldErrors(err)
      Object.entries(fields).forEach(([k, m]) => setFieldError(k as 'email', { message: m }))
      setError(errorMessage(err))
    }
  })

  const onConfirm = async () => {
    if (!pending) return
    setConfirming(true)
    setError(null)
    try {
      await confirmSignUp(pending.email, code.trim())
      await login(pending.email, pending.password)
      navigate('/app', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setConfirming(false)
    }
  }

  if (pending) {
    return (
      <AuthLayout title="Confirm your email" subtitle={`We sent a verification code to ${pending.email}.`}
        footer={<button className="font-medium text-primary hover:underline" onClick={() => resendCode(pending.email).then(() => toast.success('Code sent'), (e) => setError(errorMessage(e)))}>Resend code</button>}>
        <div className="space-y-4">
          <Field label="Verification code" htmlFor="code">
            <Input id="code" inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </Field>
          {error && <p role="alert" className="rounded-lg bg-danger-soft px-3 py-2 text-[13px] text-danger">{error}</p>}
          <Button className="w-full justify-center" onClick={onConfirm} loading={confirming} disabled={!code.trim()}>Confirm and sign in</Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Create your account" subtitle={config?.auth_mode === 'cognito' ? 'Secured by Amazon Cognito.' : 'Start tracking in under a minute.'}
      footer={<>Already have an account? <Link to="/login" className="font-medium text-primary hover:underline">Sign in</Link></>}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" autoComplete="name" aria-invalid={!!errors.name} {...register('name')} />
        </Field>
        <Field label="Email" htmlFor="email" error={errors.email?.message}>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} {...register('email')} />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password?.message} hint="At least 8 characters with a letter and a number.">
          <Input id="password" type="password" autoComplete="new-password" aria-invalid={!!errors.password} {...register('password')} />
        </Field>
        <Field label="Confirm password" htmlFor="confirm" error={errors.confirm?.message}>
          <Input id="confirm" type="password" autoComplete="new-password" aria-invalid={!!errors.confirm} {...register('confirm')} />
        </Field>
        {error && <p role="alert" className="rounded-lg bg-danger-soft px-3 py-2 text-[13px] text-danger">{error}</p>}
        <Button type="submit" className="w-full justify-center" loading={isSubmitting}>Create account</Button>
      </form>
    </AuthLayout>
  )
}
