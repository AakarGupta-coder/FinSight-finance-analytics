import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { toast } from 'sonner'
import { ArrowDown, ArrowUp, ArrowUpDown, Calculator, Download, FileImage, Filter, ListChecks, Pencil, Plus, Search, Trash2, Wallet, X } from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'
import { formatDate, formatDateTime, minorToInput, parseMoneyToMinor, todayIn } from '../lib/format'
import { useApi, useDebounced, useDocumentTitle } from '../lib/hooks'
import type { Expense, ExpensePage } from '../lib/types'
import { Badge, Button, ButtonLink, Card, EmptyState, ErrorState, Input, PageHeader, Select, Skeleton, StatCard } from '../components/ui/primitives'
import { ConfirmDialog, Dialog } from '../components/ui/dialog'
import { categoryColor, cn } from '../lib/utils'

const SORTS = [
  { key: 'date', label: 'Date' },
  { key: 'description', label: 'Description' },
  { key: 'category', label: 'Category' },
  { key: 'amount', label: 'Amount' },
] as const

function ReceiptImage({ receiptId }: { receiptId: string }) {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    // Local storage streams the bytes; S3 returns a short-lived presigned URL.
    api.blob(`/receipts/${receiptId}/image`).then(async (blob) => {
      if (cancelled) return
      if (blob.type.includes('json')) {
        const { url: signed } = JSON.parse(await blob.text())
        setUrl(signed)
      } else {
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      }
    }).catch(() => !cancelled && setFailed(true))
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [receiptId])
  if (failed) return <p className="text-xs text-muted">Receipt image unavailable.</p>
  if (!url) return <Skeleton className="h-40 w-full" />
  return <img src={url} alt="Receipt" className="max-h-80 w-full rounded-lg border border-border object-contain" />
}

export function ExpenseDetail({ expense, onClose, onDeleted }: { expense: Expense | null; onClose: () => void; onDeleted: () => void }) {
  const { money, categoryName, paymentMethodName, timezone } = useAppData()
  const navigate = useNavigate()
  const [confirm, setConfirm] = useState(false)
  if (!expense) return null
  const rows: [string, React.ReactNode][] = [
    ['Amount', <span className="font-semibold tabular">{money(expense.amount_minor)}</span>],
    ['Date', formatDate(expense.date)],
    ['Category', categoryName(expense.category)],
    ['Payment method', paymentMethodName(expense.payment_method)],
    ['Merchant', expense.merchant ?? '—'],
    ['Notes', expense.notes ?? '—'],
    ['Recorded', formatDateTime(expense.created_at, timezone)],
    ['Last updated', formatDateTime(expense.updated_at, timezone)],
  ]
  return (
    <>
      <Dialog open={!!expense && !confirm} onOpenChange={(o) => !o && onClose()} title={expense.description}
        description={expense.is_demo ? 'Demo record' : undefined} size="md"
        footer={<>
          <Button variant="outline" onClick={() => setConfirm(true)}><Trash2 className="h-4 w-4" aria-hidden />Delete</Button>
          <Button onClick={() => navigate(`/app/transactions/${expense.id}/edit`)}><Pencil className="h-4 w-4" aria-hidden />Edit</Button>
        </>}>
        <dl className="divide-y divide-border text-[13px]">
          {rows.map(([k, v]) => <div key={k} className="flex justify-between gap-4 py-2"><dt className="text-muted">{k}</dt><dd className="text-right">{v}</dd></div>)}
        </dl>
        {expense.receipt_id && <div className="mt-4"><p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted"><FileImage className="h-3.5 w-3.5" aria-hidden />Attached receipt</p><ReceiptImage receiptId={expense.receipt_id} /></div>}
      </Dialog>
      <ConfirmDialog open={confirm} onOpenChange={(o) => { setConfirm(o) }} title="Delete this transaction?"
        description={`“${expense.description}” (${money(expense.amount_minor)}) will be permanently removed. Budgets and insights update automatically.`}
        onConfirm={async () => {
          try {
            await api.del(`/expenses/${expense.id}`)
            toast.success('Transaction deleted')
            onDeleted()
          } catch (err) {
            toast.error(errorMessage(err))
            throw err
          }
        }} />
    </>
  )
}

function toCsv(rows: Expense[], categoryName: (c: string) => string, pm: (p: string) => string, currency: string) {
  const esc = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v)
  const header = ['Date', 'Description', 'Merchant', 'Category', 'Payment method', `Amount (${currency})`, 'Notes']
  const lines = rows.map((e) => [e.date, e.description, e.merchant ?? '', categoryName(e.category), pm(e.payment_method), minorToInput(e.amount_minor, currency), e.notes ?? ''].map(esc).join(','))
  return [header.join(','), ...lines].join('\n')
}

export default function TransactionsPage() {
  useDocumentTitle('Transactions')
  const { money, reference, categoryName, paymentMethodName, currency, timezone } = useAppData()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const [searchText, setSearchText] = useState(params.get('search') ?? '')
  const search = useDebounced(searchText, 300)
  const [showFilters, setShowFilters] = useState(!!(params.get('start') || params.get('end') || params.get('category') || params.get('payment_method') || params.get('min') || params.get('max')))
  const [selected, setSelected] = useState<Expense | null>(null)
  const [exporting, setExporting] = useState(false)

  const get = (k: string) => params.get(k) ?? ''
  const setParam = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(params)
    Object.entries(updates).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    if (!('page' in updates)) next.delete('page')
    setParams(next, { replace: true })
  }

  useEffect(() => {
    if (search !== get('search')) setParam({ search: search || null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  const minMinor = get('min') ? parseMoneyToMinor(get('min'), currency) : null
  const maxMinor = get('max') ? parseMoneyToMinor(get('max'), currency) : null
  const query = useMemo(() => ({
    start: get('start') || undefined,
    end: get('end') || undefined,
    category: get('category') ? [get('category')] : undefined,
    payment_method: get('payment_method') ? [get('payment_method')] : undefined,
    search: get('search') || undefined,
    min_amount_minor: minMinor ?? undefined,
    max_amount_minor: maxMinor ?? undefined,
    sort: get('sort') || 'date',
    order: get('order') || 'desc',
    page: Number(get('page') || 1),
    page_size: Number(get('page_size') || 20),
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [params.toString()])
  const { data, error, loading, reload } = useApi<ExpensePage>('/expenses', query)
  // Changes whenever the visible result set changes, so the list cross-fades once per filter/page change.
  const resultKey = data?.items.map((e) => e.id).join(',') ?? ''
  const amountError =
    (get('min') && minMinor === null) || (get('max') && maxMinor === null)
      ? 'Amounts must be positive numbers with at most 2 decimals; invalid values are ignored.'
      : minMinor !== null && maxMinor !== null && minMinor > maxMinor
        ? 'Min amount is greater than max amount, so nothing can match.'
        : null

  // If the current page is past the end (e.g. after deleting the last row), go to the last page.
  useEffect(() => {
    if (data && data.items.length === 0 && data.total_count > 0 && data.page > data.total_pages) {
      setParam({ page: String(data.total_pages) })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  // Open a transaction passed via ?open=<id> (from the dashboard).
  useEffect(() => {
    const id = params.get('open')
    if (!id) return
    api.get<Expense>(`/expenses/${id}`).then(setSelected).catch(() => toast.error('Transaction not found'))
    setParam({ open: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const activeFilters = ['start', 'end', 'category', 'payment_method', 'min', 'max', 'search'].filter((k) => get(k))
  const toggleSort = (key: string) => {
    const same = query.sort === key
    setParam({ sort: key, order: same && query.order === 'desc' ? 'asc' : 'desc' })
  }

  const exportCsv = async () => {
    setExporting(true)
    try {
      const all: Expense[] = []
      for (let page = 1; page <= 50; page++) {
        const res = await api.get<ExpensePage>('/expenses', { ...query, page, page_size: 100 })
        all.push(...res.items)
        if (page >= res.total_pages) break
      }
      const blob = new Blob([toCsv(all, categoryName, paymentMethodName, currency)], { type: 'text/csv;charset=utf-8' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `transactions-${todayIn(timezone)}.csv`
      a.click()
      URL.revokeObjectURL(a.href)
      toast.success(`Exported ${all.length} transaction(s)`)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
      <PageHeader title="Transactions" description="Search, filter and manage every recorded expense."
        actions={<>
          <Button variant="outline" onClick={exportCsv} loading={exporting} disabled={!data?.total_count}><Download className="h-4 w-4" aria-hidden />Export CSV</Button>
          <ButtonLink to="/app/transactions/new"><Plus className="h-4 w-4" aria-hidden />Add expense</ButtonLink>
        </>} />

      {/* Summary strip — computed by the API over all matching transactions (not just this page). */}
      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatCard icon={<ListChecks className="h-[18px] w-[18px]" />} label={activeFilters.length ? 'Matching transactions' : 'Transactions'} loading={!data} value={data?.total_count ?? 0}
          sub={activeFilters.length ? `${activeFilters.length} filter(s) applied` : 'All recorded expenses'} />
        <StatCard emphasis icon={<Wallet className="h-[18px] w-[18px]" />} label="Total amount" loading={!data} value={money(data?.total_amount_minor ?? 0)}
          sub={get('start') || get('end') ? `${get('start') ? formatDate(get('start')) : 'Start'} – ${get('end') ? formatDate(get('end')) : 'today'}` : 'Across all dates'} />
        <StatCard icon={<Calculator className="h-[18px] w-[18px]" />} label="Average transaction" loading={!data}
          value={data && data.total_count ? money(Math.round(data.total_amount_minor / data.total_count), { round: true }) : '—'} sub="Total ÷ number of transactions" />
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
            <Input aria-label="Search transactions" placeholder="Search description, merchant or notes" className="pl-9" value={searchText} onChange={(e) => setSearchText(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <Button variant={showFilters ? 'secondary' : 'outline'} onClick={() => setShowFilters((s) => !s)} aria-expanded={showFilters}>
              <Filter className="h-4 w-4" aria-hidden />Filters{activeFilters.filter((f) => f !== 'search').length ? ` (${activeFilters.filter((f) => f !== 'search').length})` : ''}
            </Button>
            {activeFilters.length > 0 && <Button variant="ghost" onClick={() => { setSearchText(''); setParams(new URLSearchParams(), { replace: true }) }}><X className="h-4 w-4" aria-hidden />Clear</Button>}
          </div>
        </div>
        {showFilters && (
          <div className="fs-field-msg grid gap-3 border-b border-border bg-surface-2/50 p-4 sm:grid-cols-3 lg:grid-cols-6">
            <label className="text-xs font-medium text-muted">From<Input type="date" className="mt-1" value={get('start')} max={get('end') || undefined} onChange={(e) => setParam({ start: e.target.value || null })} /></label>
            <label className="text-xs font-medium text-muted">To<Input type="date" className="mt-1" value={get('end')} min={get('start') || undefined} onChange={(e) => setParam({ end: e.target.value || null })} /></label>
            <label className="text-xs font-medium text-muted">Category
              <Select className="mt-1" value={get('category')} onChange={(e) => setParam({ category: e.target.value || null })}>
                <option value="">All categories</option>
                {reference?.categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </Select></label>
            <label className="text-xs font-medium text-muted">Payment method
              <Select className="mt-1" value={get('payment_method')} onChange={(e) => setParam({ payment_method: e.target.value || null })}>
                <option value="">All methods</option>
                {reference?.payment_methods.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </Select></label>
            <label className="text-xs font-medium text-muted">Min amount<Input inputMode="decimal" className="mt-1" defaultValue={get('min')} onBlur={(e) => setParam({ min: e.target.value || null })} /></label>
            <label className="text-xs font-medium text-muted">Max amount<Input inputMode="decimal" className="mt-1" defaultValue={get('max')} onBlur={(e) => setParam({ max: e.target.value || null })} /></label>
            {amountError && <p role="alert" className="text-xs text-danger sm:col-span-3 lg:col-span-6">{amountError}</p>}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-[13px]">
          <span className="text-muted">{data ? <><strong className="text-text">{data.total_count}</strong> transaction(s) · total <strong className="tabular text-text">{money(data.total_amount_minor)}</strong></> : ' '}</span>
          <label className="flex items-center gap-2 text-xs text-muted">Rows
            <Select className="h-8 w-20" value={String(query.page_size)} onChange={(e) => setParam({ page_size: e.target.value })}>
              {[10, 20, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
            </Select>
          </label>
        </div>

        {error ? <ErrorState error={error} onRetry={reload} /> : !data ? (
          <div className="space-y-2 p-4">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
        ) : data.items.length === 0 ? (
          activeFilters.length
            ? <EmptyState className="fs-rise-in" icon={<Search className="h-5 w-5" />} title="No matching transactions" description="Try widening the date range or clearing filters." />
            : <EmptyState className="fs-rise-in" icon={<Plus className="h-5 w-5" />} title="No transactions yet" description="Use Add expense above to record your first expense." />
        ) : (
          <>
            {/* Desktop table */}
            <div className={cn('fs-refreshable hidden overflow-x-auto md:block', loading && 'fs-refreshing')} aria-busy={loading || undefined}>
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-y border-border bg-surface-2 text-left text-xs text-muted">
                    {SORTS.map((s) => (
                      <th key={s.key} scope="col" className={cn('px-4 py-2 font-medium', s.key === 'amount' && 'text-right')}
                        aria-sort={query.sort === s.key ? (query.order === 'asc' ? 'ascending' : 'descending') : 'none'}>
                        <button type="button" onClick={() => toggleSort(s.key)} className="inline-flex items-center gap-1 hover:text-text">
                          {s.label}
                          {query.sort === s.key ? (query.order === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-50" />}
                        </button>
                      </th>
                    ))}
                    <th scope="col" className="px-4 py-2 font-medium">Payment</th>
                    <th scope="col" className="px-4 py-2"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody key={resultKey} className="fs-fade-in divide-y divide-border">
                  {data.items.map((e) => (
                    <tr key={e.id} className="cursor-pointer transition-colors duration-100 hover:bg-surface-2" onClick={() => setSelected(e)}>
                      <td className="whitespace-nowrap px-4 py-2.5 text-text-2">{formatDate(e.date)}</td>
                      <td className="max-w-[320px] px-4 py-2.5">
                        <button type="button" className="block max-w-full truncate text-left font-medium hover:underline" onClick={(ev) => { ev.stopPropagation(); setSelected(e) }}>{e.description}</button>
                        <span className="block truncate text-xs text-muted">{e.merchant ?? ''}{e.receipt_id ? ' · receipt attached' : ''}</span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="inline-flex items-center gap-1.5 text-text-2"><span className="h-2 w-2 rounded-full" style={{ background: categoryColor(e.category) }} aria-hidden />{categoryName(e.category)}</span> {e.is_demo && <Badge>Demo</Badge>}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-right font-semibold tabular">{money(e.amount_minor)}</td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-text-2">{paymentMethodName(e.payment_method)}</td>
                      <td className="px-4 py-2.5 text-right">
                        <Button variant="ghost" size="icon" aria-label={`Edit ${e.description}`} onClick={(ev) => { ev.stopPropagation(); navigate(`/app/transactions/${e.id}/edit`) }}><Pencil className="h-4 w-4" /></Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Mobile list */}
            <ul key={resultKey} className={cn('fs-fade-in fs-refreshable divide-y divide-border border-t border-border md:hidden', loading && 'fs-refreshing')}>
              {data.items.map((e) => (
                <li key={e.id}>
                  <button type="button" onClick={() => setSelected(e)} className="flex w-full items-center gap-3 px-4 py-3 text-left">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13.5px] font-medium">{e.description}</p>
                      <p className="truncate text-xs text-muted">{formatDate(e.date)} · {categoryName(e.category)}</p>
                    </div>
                    <span className="font-semibold tabular">{money(e.amount_minor)}</span>
                  </button>
                </li>
              ))}
            </ul>
            <nav className="flex items-center justify-between border-t border-border px-4 py-3 text-[13px]" aria-label="Pagination">
              <span className="text-muted">Page {data.page} of {data.total_pages}</span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={data.page <= 1} onClick={() => setParam({ page: String(data.page - 1) })}>Previous</Button>
                <Button variant="outline" size="sm" disabled={data.page >= data.total_pages} onClick={() => setParam({ page: String(data.page + 1) })}>Next</Button>
              </div>
            </nav>
          </>
        )}
      </Card>

      <ExpenseDetail expense={selected} onClose={() => setSelected(null)} onDeleted={() => { setSelected(null); reload() }} />
    </>
  )
}
