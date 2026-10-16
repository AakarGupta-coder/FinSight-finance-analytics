import { Loader2 } from 'lucide-react'
import { useId } from 'react'
import { cn } from '../../lib/utils'

export const BRAND = {
  name: 'FinSight',
  tagline: 'Understand Your Spending. Make Smarter Financial Decisions.',
  fullTitle: 'Cloud-Based Personal Finance Intelligence & Expense Analytics Platform',
  documentTitle: 'FinSight — Personal Finance Intelligence',
}

/** The FinSight mark: an "F" whose top arm rises like a trend line to a data point. Same geometry as public/favicon.svg. */
export function BrandMark({ className }: { className?: string }) {
  const id = useId()
  return (
    <svg viewBox="0 0 32 32" className={cn('h-8 w-8 shrink-0', className)} aria-hidden focusable="false">
      <defs>
        <linearGradient id={`${id}-g`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#10B981" />
          <stop offset="100%" stopColor="#065F46" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="7.5" fill={`url(#${id}-g)`} />
      <path d="M10.5 24.5V11H16.25L22.5 6.5" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10.5 17.75H17.5" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" />
      <circle cx="22.5" cy="6.5" r="2.4" fill="#A7F3D0" />
    </svg>
  )
}

/** Mark + "FinSight" wordmark. */
export function BrandLogo({ size = 'md', hideWordmarkOnMobile = false, className }: {
  size?: 'sm' | 'md' | 'lg'; hideWordmarkOnMobile?: boolean; className?: string
}) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <BrandMark className={size === 'lg' ? 'h-10 w-10' : size === 'sm' ? 'h-7 w-7' : 'h-8 w-8'} />
      <span className={cn('font-semibold tracking-tight text-text', size === 'lg' ? 'text-xl' : 'text-[16px]',
        hideWordmarkOnMobile && 'hidden sm:inline')}>
        Fin<span className="text-emerald">Sight</span>
      </span>
    </span>
  )
}

/** Full-screen branded loading state (session check, workspace load). */
export function BrandedLoader({ label }: { label: string }) {
  return (
    <div role="status" className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-muted">
      <BrandMark className="h-11 w-11 animate-[fs-pulse_1.6s_ease-in-out_infinite]" />
      <span className="flex items-center gap-2 text-sm"><Loader2 className="h-4 w-4 animate-spin text-emerald" aria-hidden />{label}…</span>
    </div>
  )
}
