import { forwardRef, useEffect, useState, type AnchorHTMLAttributes, type ButtonHTMLAttributes, type HTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import { Link } from 'react-router'
import { AlertCircle, AlertTriangle, Loader2, RefreshCw } from 'lucide-react'
import { cn } from '../../lib/utils'
import { useCountUp } from '../../lib/motion'
import { errorMessage } from '../../lib/api'

/* Design tokens (see index.css):
   radii   — cards/dialogs rounded-2xl (16px); buttons, inputs, segmented rounded-[10px]; chips rounded-full
   heights — button/input 36px (md), 32px (sm)
   spacing — card padding 20px (px-5), grid gap 16px (gap-4), section gap 16px (mt-4) */

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
type Size = 'sm' | 'md' | 'icon'

const buttonBase =
  'inline-flex items-center justify-center rounded-[10px] font-medium whitespace-nowrap select-none ' +
  'transition-[background-color,border-color,color,box-shadow,opacity,transform] duration-150 ease-out active:scale-[0.97] ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] ' +
  'disabled:pointer-events-none disabled:opacity-45 disabled:shadow-none'

const variants: Record<Variant, string> = {
  primary: 'bg-primary text-primary-fg shadow-btn hover:bg-primary-hover',
  secondary: 'border border-border bg-surface-3 text-text hover:border-border-strong',
  outline: 'border border-border bg-surface-2 text-text hover:bg-surface-3 hover:border-border-strong',
  ghost: 'text-text-2 hover:bg-surface-3 hover:text-text',
  danger: 'bg-danger text-white shadow-btn hover:brightness-95 focus-visible:ring-[var(--ring-danger)]',
}
const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-[12.5px] gap-1.5',
  md: 'h-9 px-3.5 text-[13px] gap-2',
  icon: 'h-9 w-9',
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading, className, children, disabled, type = 'button', ...props }, ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(buttonBase, variants[variant], sizes[size], className)}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  )
})

/** A router link styled as a button (avoids nesting a <button> inside an <a>). */
export function ButtonLink({ to, variant = 'primary', size = 'md', className, children, ...rest }: {
  to: string; variant?: Variant; size?: Size; className?: string; children: ReactNode
} & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'>) {
  return (
    <Link to={to} className={cn(buttonBase, variants[variant], sizes[size], className)} {...rest}>
      {children}
    </Link>
  )
}

/** Text link used for a card's single contextual navigation ("View all", "Budgets"). */
export function CardLink({ to, children, className }: { to: string; children: ReactNode; className?: string }) {
  return (
    <Link to={to} className={cn('inline-flex h-7 items-center rounded-lg border border-border bg-surface-2 px-2.5 text-[12px] font-medium text-text-2 transition-colors hover:border-border-strong hover:text-text', className)}>
      {children}
    </Link>
  )
}

type CardVariant = 'default' | 'raised' | 'muted' | 'glass' | 'featured'
const cardVariants: Record<CardVariant, string> = {
  // Solid surfaces for data; the emerald-lit "featured" surface is used once per screen at most.
  default: 'border-border bg-surface shadow-card',
  raised: 'border-border bg-surface edge-highlight',
  muted: 'border-border bg-surface-2',
  glass: 'glass border-glass-border shadow-raised',
  featured: 'ambient border-border shadow-card',
}

export function Card({ className, variant = 'default', ...props }: HTMLAttributes<HTMLDivElement> & { variant?: CardVariant }) {
  return <div className={cn('rounded-2xl border', cardVariants[variant], className)} {...props} />
}

export function CardHeader({ title, description, action, className }: { title: ReactNode; description?: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div className={cn('flex items-start justify-between gap-3 px-5 pt-4 pb-3', className)}>
      <div className="min-w-0">
        <h2 className="text-[14px] font-medium text-text">{title}</h2>
        {description && <p className="mt-0.5 text-[12px] leading-snug text-muted">{description}</p>}
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </div>
  )
}

export function CardBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('px-5 pb-5', className)} {...props} />
}

const fieldBase =
  'w-full rounded-[10px] border border-border bg-surface-2 px-3 text-[13.5px] text-text placeholder:text-muted ' +
  'transition-[border-color,box-shadow,background-color] duration-150 hover:border-border-strong ' +
  'focus:border-emerald focus:bg-surface focus:outline-none focus:ring-2 focus:ring-[var(--ring)] ' +
  'disabled:cursor-not-allowed disabled:opacity-60 ' +
  'aria-[invalid=true]:border-danger aria-[invalid=true]:focus:ring-[var(--ring-danger)]'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...props }, ref) {
  return <input ref={ref} className={cn(fieldBase, 'h-9', className)} {...props} />
})

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select({ className, children, ...props }, ref) {
  return <select ref={ref} className={cn(fieldBase, 'fs-select h-9 cursor-pointer pr-9', className)} {...props}>{children}</select>
})

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(fieldBase, 'min-h-[76px] py-2', className)} {...props} />
})

export function Field({ label, htmlFor, error, hint, children, className, required }: {
  label: string; htmlFor: string; error?: string; hint?: ReactNode; children: ReactNode; className?: string; required?: boolean
}) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={htmlFor} className="block text-[12.5px] font-medium text-text-2">
        {label}{required && <span className="text-danger" aria-hidden> *</span>}
      </label>
      {children}
      {error ? (
        <p id={`${htmlFor}-error`} role="alert" className="fs-field-msg flex items-start gap-1 text-xs text-danger">
          <AlertCircle className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden />{error}
        </p>
      ) : hint ? <p className="text-xs text-muted">{hint}</p> : null}
    </div>
  )
}

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'primary'
const tones: Record<Tone, string> = {
  neutral: 'bg-surface-3 text-text-2 border-border',
  success: 'bg-success-soft text-success border-transparent',
  warning: 'bg-warning-soft text-warning border-transparent',
  danger: 'bg-danger-soft text-danger border-transparent',
  info: 'bg-info-soft text-info border-transparent',
  primary: 'bg-primary-soft text-accent border-transparent',
}

export function Badge({ tone = 'neutral', className, children, icon }: { tone?: Tone; className?: string; children: ReactNode; icon?: ReactNode }) {
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-4 whitespace-nowrap', tones[tone], className)}>
      {icon}{children}
    </span>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton rounded-lg', className)} aria-hidden />
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-12 text-muted">
      <Loader2 className="h-5 w-5 animate-spin text-emerald" aria-hidden /> <span className="text-sm">{label}…</span>
    </div>
  )
}

export function Progress({ value, tone = 'primary', label, className }: { value: number | null; tone?: 'primary' | 'success' | 'warning' | 'danger'; label: string; className?: string }) {
  const v = Math.max(0, Math.min(100, value ?? 0))
  // Bars grow from empty on first render, then glide between values on updates.
  const [shown, setShown] = useState(0)
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(v))
    return () => cancelAnimationFrame(id)
  }, [v])
  const color = { primary: 'bg-emerald', success: 'bg-emerald', warning: 'bg-warning-fill', danger: 'bg-danger' }[tone]
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-[var(--track)]', className)} role="progressbar"
      aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(v)}>
      <div className={cn('h-full rounded-full transition-[width,background-color] duration-700 ease-[var(--ease-out)]', color)} style={{ width: `${shown}%` }} />
    </div>
  )
}

export function EmptyState({ icon, title, description, action, className }: { icon?: ReactNode; title: string; description?: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col items-center justify-center px-6 py-10 text-center', className)}>
      {icon && <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface-3 text-accent">{icon}</div>}
      <h3 className="text-[13.5px] font-medium text-text">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-[12.5px] leading-relaxed text-muted">{description}</p>}
      {action && <div className="mt-4 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  return (
    <div role="alert" className={cn('flex flex-col items-center justify-center gap-3 px-6 py-10 text-center', className)}>
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-danger-soft text-danger"><AlertTriangle className="h-5 w-5" aria-hidden /></div>
      <div>
        <p className="text-sm font-medium text-text">Couldn't load this data</p>
        <p className="mt-1 text-[12.5px] text-muted">{errorMessage(error)}</p>
      </div>
      {onRetry && <Button variant="outline" size="sm" onClick={onRetry}><RefreshCw className="h-3.5 w-3.5" aria-hidden />Try again</Button>}
    </div>
  )
}

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-[20px] font-semibold leading-tight tracking-tight text-text">{title}</h1>
        {description && <p className="mt-1 text-[12.5px] text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Segmented<T extends string>({ value, onChange, options, label, size = 'md' }: {
  value: T; onChange: (v: T) => void; options: { value: T; label: string }[]; label: string; size?: 'sm' | 'md'
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap rounded-[10px] border border-border bg-surface-2 p-0.5">
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}
          className={cn('rounded-lg font-medium transition-[background-color,color,box-shadow] duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]',
            size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-[13px]',
            value === o.value ? 'bg-surface-3 text-text shadow-xs ring-1 ring-border-strong' : 'text-muted hover:text-text')}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Small change indicator: arrow tile + signed percentage (reference KPI style). */
export function TrendChip({ value, suffix = '%', goodWhenUp = false, label }: {
  value: number; suffix?: string; goodWhenUp?: boolean; label?: string
}) {
  const up = value > 0
  const flat = value === 0
  const good = flat ? null : goodWhenUp ? up : !up
  const tone = good === null ? 'text-text-2 bg-surface-3' : good ? 'text-success bg-success-soft' : 'text-danger bg-danger-soft'
  return (
    <span className="inline-flex items-center gap-1.5" title={label}>
      <span className={cn('flex h-6 w-6 items-center justify-center rounded-lg border border-border', tone)} aria-hidden>
        <svg viewBox="0 0 16 16" className={cn('h-3.5 w-3.5', !flat && !up && 'rotate-90')} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          {flat ? <path d="M3.5 8h9" /> : <><path d="M5 11 11 5" /><path d="M6 5h5v5" /></>}
        </svg>
      </span>
      <span className={cn('text-[12.5px] font-medium tabular', good === null ? 'text-text-2' : good ? 'text-success' : 'text-danger')}>
        {up ? '+' : ''}{value}{suffix}
      </span>
      {label && <span className="sr-only">{label}</span>}
    </span>
  )
}

/** KPI card in the reference style: label + small icon on top, large figure, optional chip and sub-line. */
export function StatCard({ label, value, sub, icon, loading, tone, emphasis = false, chip }: {
  label: string; value: ReactNode; sub?: ReactNode; icon?: ReactNode; loading?: boolean; tone?: 'danger' | 'success' | 'warning'
  /** Featured KPI: emerald-lit surface (one per screen). */
  emphasis?: boolean
  chip?: ReactNode
}) {
  return (
    <Card variant={emphasis ? 'featured' : 'default'} className="flex min-h-[112px] flex-col p-4 sm:px-5">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-[13px] text-text-2">{label}</p>
        {icon && <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-text-2 [&>svg]:h-3.5 [&>svg]:w-3.5" aria-hidden>{icon}</span>}
      </div>
      {loading ? <Skeleton className="mt-3 h-7 w-32" /> : (
        <div className="fs-fade-in mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1">
          <p className={cn('truncate text-[24px] font-semibold leading-8 tracking-tight tabular text-text',
            tone === 'danger' && 'text-danger', tone === 'success' && 'text-success', tone === 'warning' && 'text-warning')}>{value}</p>
          {chip}
        </div>
      )}
      {sub && !loading && <div className="mt-auto truncate pt-1 text-[12px] text-muted">{sub}</div>}
    </Card>
  )
}

/** A figure that counts from its previous value to the new one (formatted on every frame). */
export function AnimatedNumber({ value, format, duration }: { value: number; format: (v: number) => ReactNode; duration?: number }) {
  const current = useCountUp(value, duration)
  // Intermediate frames show whole units (no flickering paise); the final frame is exact.
  const frame = current === value ? value : Math.round(current / 100) * 100
  // Screen readers get the final figure only, not every intermediate frame.
  return <><span aria-hidden>{format(frame)}</span><span className="sr-only">{format(value)}</span></>
}

/** Settings-style section: title + description on the left, controls on the right (stacks on mobile). */
export function SettingsSection({ title, description, children, className, danger = false }: {
  title: string; description?: ReactNode; children: ReactNode; className?: string; danger?: boolean
}) {
  return (
    <section className={cn('grid gap-3 border-b border-border px-5 py-4 last:border-b-0 md:grid-cols-[240px_1fr] md:gap-8', className)}>
      <div>
        <h2 className={cn('text-[13.5px] font-medium', danger ? 'text-danger' : 'text-text')}>{title}</h2>
        {description && <p className="mt-1 text-[12px] leading-relaxed text-muted">{description}</p>}
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  )
}
