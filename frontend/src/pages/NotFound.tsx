import { Link } from 'react-router'
import { Compass } from 'lucide-react'
import { useDocumentTitle } from '../lib/hooks'
import { ButtonLink } from '../components/ui/primitives'

const SUGGESTIONS = [
  { to: '/app', label: 'Dashboard' },
  { to: '/app/transactions', label: 'Transactions' },
  { to: '/app/budgets', label: 'Budgets' },
  { to: '/app/assistant', label: 'Assistant' },
]

export default function NotFoundPage({ inApp = false }: { inApp?: boolean }) {
  useDocumentTitle('Page not found')
  return (
    <div className={inApp ? 'py-16' : 'flex min-h-full items-center justify-center bg-bg px-4 py-16'}>
      <div className="mx-auto max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary-soft text-primary"><Compass className="h-6 w-6" aria-hidden /></div>
        <p className="mt-4 text-sm font-semibold text-primary">404</p>
        <h1 className="mt-1 text-xl font-semibold">We couldn't find that page</h1>
        <p className="mt-2 text-[13px] text-muted">The link may be outdated or mistyped. Here are some places you might be looking for:</p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {SUGGESTIONS.map((s) => <ButtonLink key={s.to} to={s.to} variant="outline" size="sm">{s.label}</ButtonLink>)}
        </div>
        {!inApp && <Link to="/" className="mt-6 inline-block text-[13px] font-medium text-primary hover:underline">Back to home</Link>}
      </div>
    </div>
  )
}
