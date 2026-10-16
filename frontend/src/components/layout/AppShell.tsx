import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router'
import {
  ArrowLeftRight, Bell, Bot, ChartLine, CornerDownLeft, FlaskConical, LayoutDashboard, LogOut, Menu, Moon, PiggyBank, ScanLine,
  Search, Settings, ShieldAlert, Sparkles, Sun, User, Wallet, X, type LucideIcon,
} from 'lucide-react'
import { useAuth } from '../../lib/auth'
import { useAppData } from '../../lib/appData'
import { useApi } from '../../lib/hooks'
import { cn, useCurrentTheme } from '../../lib/utils'
import { Button, ErrorState } from '../ui/primitives'
import { BrandedLoader, BrandMark } from '../brand/Brand'

interface NavItem { to: string; label: string; icon: LucideIcon; end?: boolean }

/** Navigation groups (sidebar, mobile drawer and the header's quick search all use this list). */
export const NAV: { group: string; items: NavItem[] }[] = [
  { group: 'Overview', items: [
    { to: '/app', label: 'Dashboard', icon: LayoutDashboard, end: true },
  ] },
  { group: 'Money management', items: [
    { to: '/app/transactions', label: 'Transactions', icon: ArrowLeftRight },
    { to: '/app/budgets', label: 'Budgets', icon: Wallet },
    { to: '/app/analytics', label: 'Analytics', icon: ChartLine },
  ] },
  { group: 'Financial intelligence', items: [
    { to: '/app/insights', label: 'Financial insights', icon: Sparkles },
    { to: '/app/anomalies', label: 'Anomaly detection', icon: ShieldAlert },
    { to: '/app/receipts', label: 'Receipt scanner', icon: ScanLine },
    { to: '/app/simulator', label: 'What-If simulator', icon: FlaskConical },
    { to: '/app/assistant', label: 'Finance assistant', icon: Bot },
  ] },
  { group: 'Financial planning', items: [
    { to: '/app/goals', label: 'Savings goals', icon: PiggyBank },
  ] },
  { group: 'Preferences', items: [
    { to: '/app/profile', label: 'Profile', icon: User },
    { to: '/app/settings', label: 'Settings', icon: Settings },
  ] },
]

const FLAT = NAV.flatMap((s) => s.items.map((i) => ({ ...i, group: s.group })))

/** Nav entry that owns a path (longest matching prefix), e.g. /app/transactions/new → Transactions. */
function sectionFor(pathname: string) {
  return [...FLAT].sort((a, b) => b.to.length - a.to.length).find((i) => (i.end ? pathname === i.to : pathname === i.to || pathname.startsWith(`${i.to}/`)))
}

function ThemeToggle({ className }: { className?: string }) {
  const { isDark, toggleTheme } = useCurrentTheme()
  const label = isDark ? 'Switch to light theme' : 'Switch to dark theme'
  return (
    <button type="button" onClick={toggleTheme} aria-label={label} title={label}
      className={cn('inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-text-2 transition-colors hover:border-border-strong hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]', className)}>
      {/* Keyed so the new icon rotates in when the theme flips. */}
      {isDark ? <Sun key="sun" className="fs-icon-swap h-4 w-4" aria-hidden /> : <Moon key="moon" className="fs-icon-swap h-4 w-4" aria-hidden />}
    </button>
  )
}

function Avatar({ name, className }: { name: string; className?: string }) {
  return (
    <span className={cn('brand-gradient flex shrink-0 items-center justify-center rounded-full text-[12px] font-semibold text-white', className)} aria-hidden>
      {name.slice(0, 1).toUpperCase()}
    </span>
  )
}

function useUserLabel() {
  const { user } = useAuth()
  const { me } = useAppData()
  return {
    name: me?.preferences.display_name || me?.user.name || user?.name || 'Account',
    email: me?.user.email || user?.email || '',
  }
}

/* ------------------------------------------------------------------ sidebar */

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { logout } = useAuth()
  const { name, email } = useUserLabel()
  return (
    <>
      <div className="p-3">
        <Link to="/app" onClick={onNavigate} aria-label="FinSight dashboard"
          className="flex items-center gap-2.5 rounded-xl border border-border bg-surface-2 px-3 py-2.5 transition-colors hover:border-border-strong">
          <BrandMark className="h-8 w-8" />
          <span className="min-w-0">
            <span className="block text-[14px] font-semibold leading-tight tracking-tight text-text">FinSight</span>
            <span className="block truncate text-[11px] text-muted">Finance intelligence</span>
          </span>
        </Link>
      </div>

      <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 pb-3">
        {NAV.map((section) => (
          <div key={section.group} className="mt-3 first:mt-1">
            <p className="px-2 pb-1.5 text-[10.5px] font-medium uppercase tracking-[0.08em] text-muted">{section.group}</p>
            <ul className="space-y-0.5">
              {section.items.map(({ to, label, icon: Icon, end }) => (
                <li key={to}>
                  <NavLink to={to} end={end} onClick={onNavigate}
                    className={({ isActive }) => cn(
                      'nav-item group flex h-9 items-center gap-2.5 rounded-[10px] border px-2.5 text-[13px] transition-[background-color,border-color,color] duration-150',
                      isActive
                        ? 'edge-highlight border-border bg-surface-3 font-medium text-text'
                        : 'border-transparent text-text-2 hover:bg-surface-2 hover:text-text',
                    )}>
                    {({ isActive }) => <>
                      <Icon className={cn('h-4 w-4 shrink-0', isActive ? 'text-emerald' : 'text-muted group-hover:text-text-2')} aria-hidden />
                      <span className="truncate">{label}</span>
                    </>}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="p-3 pt-0">
        <div className="ambient-top flex items-center gap-2.5 rounded-xl border border-border p-2.5">
          <Avatar name={name} className="h-8 w-8" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[12.5px] font-medium text-text">{name}</p>
            <p className="truncate text-[11px] text-muted">{email}</p>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => { onNavigate?.(); logout() }} aria-label="Sign out" title="Sign out">
            <LogOut className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </div>
    </>
  )
}

/* ------------------------------------------------------------------ quick search */

interface SearchOption { key: string; label: string; hint: string; to: string; icon: LucideIcon }

/** Header search: jump to any page, or search transactions for the typed text (Ctrl/⌘ + K). */
function QuickSearch() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)

  const options = useMemo<SearchOption[]>(() => {
    const q = query.trim().toLowerCase()
    const pages = FLAT.filter((i) => !q || i.label.toLowerCase().includes(q) || i.group.toLowerCase().includes(q))
      .map((i) => ({ key: i.to, label: i.label, hint: i.group, to: i.to, icon: i.icon }))
    const txn = q ? [{ key: 'txn', label: `Search transactions for “${query.trim()}”`, hint: 'Transactions', to: `/app/transactions?search=${encodeURIComponent(query.trim())}`, icon: Search }] : []
    // Page matches first; the transaction search is always offered as the last option.
    return [...pages.slice(0, 7), ...txn]
  }, [query])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
        setOpen(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  useEffect(() => setActive(0), [query])

  const go = (o: SearchOption | undefined) => {
    if (!o) return
    navigate(o.to)
    setQuery('')
    setOpen(false)
    inputRef.current?.blur()
  }

  return (
    <div className="relative hidden w-full max-w-[360px] md:block">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
      <input ref={inputRef} type="text" role="combobox" aria-expanded={open} aria-controls="quick-search-list" aria-autocomplete="list"
        aria-activedescendant={open && options[active] ? `qs-${active}` : undefined}
        aria-label="Search pages or transactions" placeholder="Search or jump to a page"
        value={query} onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, options.length - 1)) }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
          else if (e.key === 'Enter') { e.preventDefault(); go(options[active]) }
          else if (e.key === 'Escape') { setOpen(false); inputRef.current?.blur() }
        }}
        className="h-10 w-full rounded-xl border border-border bg-surface pl-9 pr-24 text-[13px] text-text placeholder:text-muted transition-colors hover:border-border-strong focus:border-emerald focus:outline-none focus:ring-2 focus:ring-[var(--ring)]" />
      <kbd className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 rounded-lg bg-primary px-2 py-1 font-sans text-[11px] font-medium text-primary-fg">
        {isMac ? '⌘' : 'Ctrl'} + K
      </kbd>
      {open && options.length > 0 && (
        <ul id="quick-search-list" role="listbox" aria-label="Search results"
          className="glass-strong absolute left-0 right-0 top-[calc(100%+6px)] z-40 overflow-hidden rounded-xl border p-1 shadow-float">
          {options.map((o, i) => (
            <li key={o.key} id={`qs-${i}`} role="option" aria-selected={i === active}
              onMouseDown={(e) => { e.preventDefault(); go(o) }} onMouseEnter={() => setActive(i)}
              className={cn('flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px]', i === active ? 'bg-surface-3 text-text' : 'text-text-2')}>
              <o.icon className={cn('h-4 w-4 shrink-0', i === active ? 'text-emerald' : 'text-muted')} aria-hidden />
              <span className="min-w-0 flex-1 truncate">{o.label}</span>
              <span className="shrink-0 text-[11px] text-muted">{o.hint}</span>
              {i === active && <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden />}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Open anomaly alerts — the app's in-product notifications. */
function AlertsBell() {
  const location = useLocation()
  const { data, reload } = useApi<{ counts: Record<string, number> }>('/anomalies', { status: 'open' })
  // Refresh when navigating so the count reflects reviews done on other pages (skip the initial mount).
  const firstPath = useRef(location.pathname)
  useEffect(() => {
    if (location.pathname !== firstPath.current) reload()
    firstPath.current = ''
  }, [location.pathname, reload])
  const open = data?.counts.open ?? 0
  const label = open ? `${open} open anomaly alert${open === 1 ? '' : 's'}` : 'No open anomaly alerts'
  return (
    <Link to="/app/anomalies" aria-label={label} title={label}
      className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-text-2 transition-colors hover:border-border-strong hover:text-text">
      <Bell className="h-4 w-4" aria-hidden />
      {open > 0 && (
        <span key={open} className="fs-pop-in absolute -right-1 -top-1 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-warning-fill px-1 text-[10px] font-semibold text-black tabular" aria-hidden>
          {open > 99 ? '99+' : open}
        </span>
      )}
    </Link>
  )
}

/* ------------------------------------------------------------------ shell */

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  // The drawer stays mounted briefly after closing so it can slide out.
  const [drawerMounted, setDrawerMounted] = useState(false)
  useEffect(() => {
    if (mobileOpen) { setDrawerMounted(true); return }
    const id = window.setTimeout(() => setDrawerMounted(false), 170)
    return () => window.clearTimeout(id)
  }, [mobileOpen])
  const location = useLocation()
  const { loading, error, reload } = useAppData()
  const { name, email } = useUserLabel()
  const section = sectionFor(location.pathname)

  useEffect(() => {
    setMobileOpen(false)
    document.getElementById('main')?.focus({ preventScroll: true })
    void window.scrollTo(0, 0)
  }, [location.pathname])
  useEffect(() => {
    if (!mobileOpen) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setMobileOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [mobileOpen])

  return (
    <div className="min-h-full">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-md focus:bg-surface focus:px-3 focus:py-2 focus:shadow">Skip to content</a>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[236px] flex-col border-r border-border bg-sidebar lg:flex" aria-label="Sidebar">
        <SidebarContent />
      </aside>

      {/* Mobile / tablet drawer */}
      {drawerMounted && (
        <div className={cn('fixed inset-0 z-50 lg:hidden', !mobileOpen && 'pointer-events-none')} role="dialog" aria-modal="true" aria-label="Navigation" aria-hidden={!mobileOpen || undefined}>
          <div className="fs-overlay absolute inset-0 bg-[var(--overlay)] backdrop-blur-[2px]" data-state={mobileOpen ? 'open' : 'closed'} onClick={() => setMobileOpen(false)} />
          <aside data-state={mobileOpen ? 'open' : 'closed'} className="fs-drawer absolute inset-y-0 left-0 flex w-[272px] max-w-[85vw] flex-col border-r border-border bg-sidebar shadow-float">
            <Button variant="ghost" size="icon" className="absolute right-2 top-2 z-10 h-8 w-8" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X className="h-4 w-4" /></Button>
            <SidebarContent onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="canvas-glow min-h-full lg:pl-[236px]">
        <header className="glass sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border px-4 sm:px-6 lg:px-7">
          <Button variant="ghost" size="icon" className="-ml-1.5 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
            <Menu className="h-5 w-5" />
          </Button>
          <Link to="/app" aria-label="FinSight dashboard" className="lg:hidden"><BrandMark className="h-7 w-7" /></Link>
          <p className="hidden min-w-0 shrink-0 truncate text-[14px] text-text-2 sm:block lg:min-w-[150px]">{section?.group ?? 'FinSight'}</p>

          <QuickSearch />

          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <AlertsBell />
            <Link to="/app/profile" title="Profile & account"
              className="flex items-center gap-2.5 rounded-full py-1 pl-1 pr-1 transition-colors hover:bg-surface-2 sm:pr-3">
              <Avatar name={name} className="h-8 w-8" />
              <span className="hidden min-w-0 leading-tight sm:block">
                <span className="block max-w-[150px] truncate text-[13px] font-medium text-text">{name}</span>
                <span className="block max-w-[150px] truncate text-[11px] text-muted">{email}</span>
              </span>
            </Link>
          </div>
        </header>

        <main id="main" tabIndex={-1} className="mx-auto max-w-[1600px] px-4 py-5 focus:outline-none sm:px-6 lg:px-7">
          {loading ? <BrandedLoader label="Loading your workspace" /> : error ? <ErrorState error={error} onRetry={reload} /> : (
            <div key={location.pathname} className="page-enter"><Outlet /></div>
          )}
        </main>
      </div>
    </div>
  )
}
