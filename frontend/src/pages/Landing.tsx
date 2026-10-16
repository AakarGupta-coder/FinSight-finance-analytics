import { ArrowRight, Bot, CheckCircle2, FlaskConical, Lock, PiggyBank, ScanLine, ShieldAlert, Sparkles, Wallet } from 'lucide-react'
import { useAuth } from '../lib/auth'
import { useDocumentTitle } from '../lib/hooks'
import { ButtonLink } from '../components/ui/primitives'
import { BRAND, BrandLogo } from '../components/brand/Brand'
import { AboutAuthorButton, AboutAuthorLink, AUTHOR } from '../components/AboutAuthor'

const FEATURES = [
  { icon: Wallet, title: 'Expenses & budgets', text: 'Record spending in seconds, set monthly and category budgets, and get one alert per threshold — not a flood.' },
  { icon: Sparkles, title: 'Evidence-based insights', text: 'Every insight shows the calculation, period and transactions behind it, labelled as fact, estimate or projection.' },
  { icon: ShieldAlert, title: 'Anomaly review', text: 'Robust statistics flag unusually large charges and likely duplicates for you to review — nothing is changed automatically.' },
  { icon: ScanLine, title: 'Receipt scanner', text: 'Open-source OCR reads merchant, date, total and tax. You review every field before anything is saved.' },
  { icon: FlaskConical, title: 'What-If simulator', text: 'Model cutting a category by a percentage or amount and compare scenarios side by side without touching real records.' },
  { icon: Bot, title: 'Finance assistant', text: 'Ask "How much did I spend on food last month?" and get an answer computed from your own data.' },
  { icon: PiggyBank, title: 'Savings goals', text: 'Track progress, required monthly contributions and whether you are on schedule.' },
  { icon: Lock, title: 'Private by design', text: 'Every request is authenticated and scoped to your account. Receipts are stored privately.' },
]

/** Static, low-opacity decorative shapes behind the hero (hidden from assistive tech). */
function HeroBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute -left-24 -top-24 h-80 w-80 rounded-full bg-primary/10 blur-3xl" />
      <div className="absolute right-[-6rem] top-10 h-96 w-96 rounded-full bg-emerald/10 blur-3xl" />
      <svg className="absolute inset-x-0 top-0 h-full w-full opacity-[0.35] dark:opacity-[0.12]" preserveAspectRatio="none">
        <defs>
          <pattern id="fs-grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <path d="M32 0H0V32" fill="none" stroke="var(--border)" strokeWidth="1" />
          </pattern>
          <linearGradient id="fs-fade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="white" stopOpacity="1" />
            <stop offset="1" stopColor="white" stopOpacity="0" />
          </linearGradient>
          <mask id="fs-mask"><rect width="100%" height="100%" fill="url(#fs-fade)" /></mask>
        </defs>
        <rect width="100%" height="100%" fill="url(#fs-grid)" mask="url(#fs-mask)" />
      </svg>
    </div>
  )
}

export default function LandingPage() {
  useDocumentTitle('')
  const { status } = useAuth()
  const signedIn = status === 'authenticated'
  return (
    <div className="min-h-full">
      <header className="glass sticky top-0 z-20 border-b">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <BrandLogo />
          <nav className="flex items-center gap-2" aria-label="Account">
            <AboutAuthorButton className="mr-0.5" />
            {signedIn ? <ButtonLink to="/app" size="sm">Open dashboard</ButtonLink> : <>
              <ButtonLink to="/login" variant="ghost" size="sm">Sign in</ButtonLink>
              <ButtonLink to="/register" size="sm">Create account</ButtonLink>
            </>}
          </nav>
        </div>
      </header>

      <main>
        <section className="relative isolate">
          <HeroBackdrop />
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.1fr_1fr] lg:py-24">
            <div className="page-enter">
              <p className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/70 px-3 py-1 text-xs font-medium text-text-2 shadow-xs">
                <span className="h-1.5 w-1.5 rounded-full bg-primary" aria-hidden />Personal finance intelligence
              </p>
              <h1 className="mt-5 text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl">
                <span className="brand-gradient-text">Understand Your Spending.</span><br />
                Make Smarter Financial Decisions.
              </h1>
              <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-text-2">
                {BRAND.name} tracks expenses, budgets, receipts and savings goals — and explains them. Insights and alerts are computed from your own records using transparent rules, so you always see why.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <ButtonLink to={signedIn ? '/app' : '/register'}>{signedIn ? 'Go to dashboard' : 'Get started — it’s free'}<ArrowRight className="h-4 w-4" aria-hidden /></ButtonLink>
              </div>
              <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-[13px] text-text-2">
                {['No bank connection needed', 'Exact money arithmetic', 'Every number explained'].map((t) => (
                  <li key={t} className="flex items-center gap-1.5"><CheckCircle2 className="h-4 w-4 text-primary" aria-hidden />{t}</li>
                ))}
              </ul>
            </div>

            <figure className="relative page-enter" aria-label="Example of how FinSight explains an insight">
              <div className="edge-highlight rounded-2xl border border-border bg-surface p-5">
                <p className="text-xs font-medium uppercase tracking-wide text-muted">Example insight</p>
                <div className="mt-3 rounded-xl border border-border bg-surface-2/60 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-warning-soft px-2 py-0.5 text-xs font-medium text-warning">Projection</span>
                    <span className="text-sm font-semibold">You may exceed your monthly budget</span>
                  </div>
                  <p className="mt-2 text-[13px] leading-relaxed text-text-2">At your current daily pace, this month's spending is projected above your budget. This is a projection, not a certainty.</p>
                  <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded-lg bg-surface p-2.5 shadow-xs"><dt className="text-muted">Calculation</dt><dd className="mt-0.5 font-medium">spent ÷ days elapsed × days in month</dd></div>
                    <div className="rounded-lg bg-surface p-2.5 shadow-xs"><dt className="text-muted">Evidence</dt><dd className="mt-0.5 font-medium">Period, values and transactions</dd></div>
                  </dl>
                </div>
                <figcaption className="mt-3 text-xs text-muted">Illustration only — your dashboard shows only your own recorded data.</figcaption>
              </div>
              {/* Small floating glass chips (decorative, no figures). */}
              <div aria-hidden className="glass absolute -left-4 -top-5 hidden items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium shadow-float sm:flex">
                <ShieldAlert className="h-4 w-4 text-warning" />Flagged for review — not judged
              </div>
              <div aria-hidden className="glass absolute -bottom-5 -right-3 hidden items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium shadow-float sm:flex">
                <Sparkles className="h-4 w-4 text-primary" />Fact · Estimate · Projection
              </div>
            </figure>
          </div>
        </section>

        <section className="border-t border-border bg-surface/80">
          <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
            <h2 className="text-xl font-semibold tracking-tight">Everything in one place</h2>
            <p className="mt-1 text-[13px] text-muted">Built for clarity: dense where you need numbers, calm everywhere else.</p>
            <ul className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {FEATURES.map(({ icon: Icon, title, text }) => (
                <li key={title} className="group rounded-xl border border-border bg-surface p-4 shadow-card transition-[box-shadow,border-color] duration-200 hover:border-border-strong hover:shadow-raised">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-soft text-primary"><Icon className="h-[18px] w-[18px]" aria-hidden /></span>
                  <h3 className="mt-3 text-sm font-semibold">{title}</h3>
                  <p className="mt-1 text-[13px] leading-relaxed text-muted">{text}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-3 px-4 py-7 text-center text-xs text-muted sm:flex-row sm:justify-between sm:text-left sm:px-6">
          <div>
            <p><span className="font-medium text-text-2">{BRAND.name}</span> — {BRAND.fullTitle}</p>
            <p className="mt-1">Not financial advice</p>
          </div>
          <p className="flex items-center gap-1.5">
            <span>Created by</span>
            <AboutAuthorLink>{AUTHOR.name}</AboutAuthorLink>
          </p>
        </div>
      </footer>
    </div>
  )
}
