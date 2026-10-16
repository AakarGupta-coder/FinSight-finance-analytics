import { useState, type ReactNode } from 'react'
import { Info } from 'lucide-react'
import { cn } from '../lib/utils'
import { BRAND, BrandMark } from './brand/Brand'
import { Dialog } from './ui/dialog'

export const AUTHOR = {
  name: 'Aakar Gupta',
  role: 'Student Developer',
  institution: 'Vellore Institute of Technology, Chennai',
} as const

// Only technologies that are in the code and the deployed stack (see docs/PROJECT_DOCUMENTATION.md §6).
const STACK: { area: string; tech: string }[] = [
  { area: 'Frontend', tech: 'React, TypeScript, Vite, Tailwind CSS' },
  { area: 'Backend', tech: 'Python, FastAPI' },
  { area: 'API & hosting', tech: 'Amazon API Gateway (HTTP API) + AWS Lambda' },
  { area: 'Authentication', tech: 'Amazon Cognito' },
  { area: 'Database', tech: 'Amazon DynamoDB' },
  { area: 'Receipt storage', tech: 'Amazon S3 (private bucket)' },
  { area: 'Receipt OCR', tech: 'Tesseract in a container Lambda' },
  { area: 'Monitoring', tech: 'Amazon CloudWatch' },
  { area: 'Infrastructure', tech: 'AWS SAM / CloudFormation' },
]

export function AboutAuthorDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="About the author" size="md"
      description={`${BRAND.name} — ${BRAND.fullTitle}`}>
      <div className="space-y-5">
        <div className="ambient-top flex items-center gap-3.5 rounded-xl border border-border p-3.5">
          <BrandMark className="h-11 w-11 shrink-0" />
          <div className="min-w-0">
            <p className="text-[15px] font-semibold leading-tight text-text">{AUTHOR.name}</p>
            <p className="mt-0.5 text-[12.5px] text-text-2">{AUTHOR.role}</p>
            <p className="text-[12.5px] text-muted">{AUTHOR.institution}</p>
          </div>
        </div>

        <div className="space-y-3 text-[13.5px] leading-relaxed text-text-2">
          <p>
            {BRAND.name} is a project developed by {AUTHOR.name} to explore how cloud computing, serverless architecture and
            data-driven analytics can be applied to personal finance management.
          </p>
          <p>
            The platform brings together expense tracking, budgeting, financial analytics, receipt scanning, savings goals and
            financial insights in one application.
          </p>
          <p>
            The project emphasises practical cloud deployment, application security, automated testing and the integration of
            managed AWS services.
          </p>
        </div>

        <section aria-labelledby="about-stack">
          <h3 id="about-stack" className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">Built with</h3>
          <dl className="mt-2 divide-y divide-border overflow-hidden rounded-xl border border-border text-[12.5px]">
            {STACK.map((s) => (
              <div key={s.area} className="grid grid-cols-[120px_1fr] gap-3 bg-surface-2/50 px-3 py-2 sm:grid-cols-[140px_1fr]">
                <dt className="text-muted">{s.area}</dt>
                <dd className="text-text">{s.tech}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-2 text-[11.5px] text-muted">Content delivery through Amazon CloudFront is planned and not yet enabled.</p>
        </section>
      </div>
    </Dialog>
  )
}

/** Circular "i" button that opens the About the author dialog. */
export function AboutAuthorButton({ className }: { className?: string }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} aria-label="About the author" title="About the author" aria-haspopup="dialog"
        className={cn('inline-flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface text-text-2 transition-[border-color,color,transform] duration-150 hover:border-border-strong hover:text-text active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]', className)}>
        <Info className="h-4 w-4" aria-hidden />
      </button>
      <AboutAuthorDialog open={open} onOpenChange={setOpen} />
    </>
  )
}

/** Inline text trigger (e.g. the footer credit) for the same dialog. */
export function AboutAuthorLink({ children, className }: { children: ReactNode; className?: string }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} aria-haspopup="dialog"
        className={cn('rounded font-medium text-text-2 underline-offset-4 transition-colors hover:text-text hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]', className)}>
        {children}
      </button>
      <AboutAuthorDialog open={open} onOpenChange={setOpen} />
    </>
  )
}
