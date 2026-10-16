import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { AlertTriangle, CheckCircle2, FileImage, Loader2, RotateCcw, ScanLine, Trash2, Upload } from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'
import { formatDateTime } from '../lib/format'
import { useApi, useDocumentTitle } from '../lib/hooks'
import type { ExpenseMutation, ExtractedField, Receipt } from '../lib/types'
import { cn } from '../lib/utils'
import { Badge, Button, ButtonLink, Card, CardBody, CardHeader, EmptyState, ErrorState, PageHeader, Skeleton } from '../components/ui/primitives'
import { ConfirmDialog } from '../components/ui/dialog'
import { ExpenseForm, type ExpensePayload } from '../components/ExpenseForm'
import { announceMutationEffects } from '../components/feedback'

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp']

interface OcrStatus { ocr_available: boolean; upload_mode: 'direct' | 'presigned'; max_bytes: number; accepted_types: string[] }
interface PresignedUpload { receipt_id: string; upload: { url: string; fields: Record<string, string> } }

function Confidence({ field }: { field: ExtractedField<unknown> }) {
  if (field.value === null || field.value === undefined) return <Badge tone="neutral">Not found — enter manually</Badge>
  const c = field.confidence
  const tone = c >= 0.75 ? 'success' : c >= 0.5 ? 'warning' : 'danger'
  const label = c >= 0.75 ? 'High' : c >= 0.5 ? 'Medium' : 'Low'
  return <Badge tone={tone}>{label} confidence ({Math.round(c * 100)}%)</Badge>
}

const SCAN_STEPS = [
  { key: 'uploading', label: 'Upload', detail: 'Sending the image to private storage' },
  { key: 'processing', label: 'Read text', detail: 'Tesseract OCR is reading the receipt' },
  { key: 'review', label: 'Review', detail: 'Check the extracted fields' },
] as const

/** Live progress while a receipt is uploaded and read: step list, running timer, indeterminate bar. */
function ScanProgress({ stage }: { stage: 'uploading' | 'processing' }) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const started = Date.now()
    const id = window.setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 500)
    return () => window.clearInterval(id)
  }, [])
  const current = SCAN_STEPS.findIndex((s) => s.key === stage)
  return (
    <div className="fs-fade-in mx-auto max-w-sm py-10" role="status" aria-live="polite">
      <ol className="space-y-3">
        {SCAN_STEPS.map((s, i) => {
          const done = i < current
          const active = i === current
          return (
            <li key={s.key} className={cn('flex items-center gap-3 transition-opacity duration-300', !done && !active && 'opacity-45')}>
              <span className={cn('flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[12px] font-semibold transition-colors duration-300',
                done ? 'border-transparent bg-primary-soft text-accent' : active ? 'border-emerald text-emerald' : 'border-border text-muted')} aria-hidden>
                {done ? <CheckCircle2 key="done" className="fs-pop-in h-4 w-4" /> : active ? <Loader2 className="h-4 w-4 animate-spin" /> : i + 1}
              </span>
              <span className="min-w-0">
                <span className="block text-[13px] font-medium text-text">{s.label}{done && <span className="sr-only"> (done)</span>}{active && <span className="sr-only"> (in progress)</span>}</span>
                {active && <span className="fs-field-msg block text-[12px] text-muted">{s.detail}…</span>}
              </span>
            </li>
          )
        })}
      </ol>
      <div className="fs-indeterminate mt-6 h-1 rounded-full bg-[var(--track)]" aria-hidden />
      <p className="mt-2 text-center text-[11.5px] tabular text-muted">Still working · {seconds}s{seconds >= 8 ? ' — the first scan after a pause can take a little longer' : ''}</p>
    </div>
  )
}

function useObjectUrl(file: File | null) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!file) return setUrl(null)
    const u = URL.createObjectURL(file)
    setUrl(u)
    return () => URL.revokeObjectURL(u)
  }, [file])
  return url
}

export default function ReceiptsPage() {
  useDocumentTitle('Receipt scanner')
  const { money, currency, categoryName, timezone } = useAppData()
  const status = useApi<OcrStatus>('/receipts/status')
  const list = useApi<{ items: Receipt[] }>('/receipts')
  const [file, setFile] = useState<File | null>(null)
  const [receipt, setReceipt] = useState<Receipt | null>(null)
  const [stage, setStage] = useState<'idle' | 'uploading' | 'processing' | 'review' | 'saved'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [deleting, setDeleting] = useState<Receipt | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const preview = useObjectUrl(file)
  const maxBytes = status.data?.max_bytes ?? 5 * 1024 * 1024

  const reset = () => {
    setFile(null); setReceipt(null); setStage('idle'); setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const choose = useCallback((f: File | undefined | null) => {
    setError(null)
    setReceipt(null)
    setStage('idle')
    if (!f) return
    if (!ACCEPTED.includes(f.type)) return setError('Unsupported file type. Choose a JPEG, PNG or WebP image.')
    if (f.size > maxBytes) return setError(`File is too large (${(f.size / 1048576).toFixed(1)} MB). Maximum is ${Math.round(maxBytes / 1048576)} MB.`)
    setFile(f)
  }, [maxBytes])

  const process = async (id: string) => {
    setStage('processing')
    const processed = await api.post<Receipt>(`/receipts/${id}/process`)
    setReceipt(processed)
    setStage('review')
  }

  const uploadAndProcess = async () => {
    if (!file) return
    setError(null)
    setStage('uploading')
    try {
      let id: string
      if (status.data?.upload_mode === 'presigned') {
        // Direct-to-S3 upload with a short-lived presigned POST; the bucket stays private.
        const signed = await api.post<PresignedUpload>('/receipts/upload-url', { content_type: file.type, size_bytes: file.size })
        const form = new FormData()
        Object.entries(signed.upload.fields).forEach(([k, v]) => form.append(k, v))
        form.append('file', file)
        const res = await fetch(signed.upload.url, { method: 'POST', body: form })
        if (!res.ok) throw new Error('Upload to storage failed. Please try again.')
        id = signed.receipt_id
      } else {
        const form = new FormData()
        form.append('file', file)
        id = (await api.upload<Receipt>('/receipts', form)).id
      }
      await process(id)
      list.reload()
    } catch (err) {
      setError(errorMessage(err))
      setStage('idle')
      list.reload()
    }
  }

  const ex = receipt?.extracted
  const defaults = ex ? {
    amount_minor: ex.total_minor,
    date: ex.date.value,
    merchant: ex.merchant.value,
    category: (ex.suggested_category.value as string | null) ?? '',
    description: ex.merchant.value ? `Purchase at ${ex.merchant.value}` : 'Receipt purchase',
    payment_method: 'upi',
    notes: ex.line_items.length ? `Items: ${ex.line_items.slice(0, 6).map((i) => i.description).join(', ')}`.slice(0, 500) : null,
  } : undefined

  const confirm = async (payload: ExpensePayload) => {
    if (!receipt) return
    const result = await api.post<ExpenseMutation & { receipt: Receipt }>(`/receipts/${receipt.id}/confirm`, payload)
    toast.success('Expense saved from receipt', { description: `${result.expense.description} · ${money(result.expense.amount_minor)}` })
    announceMutationEffects(result, currency)
    setStage('saved')
    setReceipt(result.receipt)
    list.reload()
  }

  return (
    <>
      <PageHeader title="Receipt scanner" description="Upload a photo of a receipt. Text is read with open-source OCR (Tesseract); you review every field before saving." />

      {status.data && !status.data.ocr_available && (
        <div role="alert" className="mb-4 flex gap-2 rounded-lg bg-warning-soft px-4 py-3 text-[13px] text-warning">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span>The OCR engine is not installed on the server, so receipts can be uploaded but not read. Install Tesseract (see README) or enter the expense manually.</span>
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-2">
          <CardHeader title="1. Upload" description={`JPEG, PNG or WebP · up to ${Math.round(maxBytes / 1048576)} MB`} />
          <CardBody className="space-y-4">
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => { e.preventDefault(); setDragOver(false); choose(e.dataTransfer.files?.[0]) }}
              className={cn('flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors duration-150',
                dragOver ? 'border-primary bg-primary-soft' : 'border-border-strong bg-surface-2/40 hover:border-primary/50')}>
              {preview ? (
                <div className="fs-fade-in relative overflow-hidden rounded-lg">
                  <img src={preview} alt="Selected receipt preview" className="max-h-80 rounded-lg object-contain" />
                  {(stage === 'uploading' || stage === 'processing') && <div className="fs-scanline" aria-hidden />}
                </div>
              ) : <>
                <Upload className="h-6 w-6 text-muted" aria-hidden />
                <p className="mt-2 text-[13px] font-medium">Drag a receipt image here</p>
                <p className="text-xs text-muted">or</p>
              </>}
              <input ref={inputRef} id="receipt-file" type="file" accept={ACCEPTED.join(',')} className="sr-only" onChange={(e) => choose(e.target.files?.[0])} />
              <label htmlFor="receipt-file" className="mt-3 inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-lg border border-border-strong bg-surface px-3 text-[13px] font-medium shadow-xs transition-colors hover:bg-surface-2 focus-within:ring-[3px] focus-within:ring-[var(--ring)]">
                <FileImage className="h-4 w-4" aria-hidden />{file ? 'Choose a different image' : 'Choose image'}
              </label>
              {file && <p className="mt-2 text-xs text-muted">{file.name} · {(file.size / 1024).toFixed(0)} KB</p>}
            </div>
            {error && <p role="alert" className="fs-field-msg rounded-lg bg-danger-soft px-3 py-2 text-[13px] text-danger">{error}</p>}
            <div className="flex gap-2">
              <Button className="flex-1 justify-center" disabled={!file || stage === 'uploading' || stage === 'processing' || stage === 'review'}
                loading={stage === 'uploading' || stage === 'processing'} onClick={uploadAndProcess}>
                <ScanLine className="h-4 w-4" aria-hidden />{stage === 'uploading' ? 'Uploading' : stage === 'processing' ? 'Reading receipt' : 'Scan receipt'}
              </Button>
              {(file || receipt) && stage !== 'review' && stage !== 'uploading' && stage !== 'processing' && <Button variant="outline" onClick={reset}>Start over</Button>}
            </div>
            <p className="text-xs text-muted">Receipts are stored privately and are only accessible to your account.</p>
          </CardBody>
        </Card>

        <Card className="xl:col-span-3">
          <CardHeader title="2. Review & save" description="Extraction is an estimate. Check each field — nothing is saved until you confirm." />
          <CardBody>
            {stage === 'processing' || stage === 'uploading' ? (
              <ScanProgress stage={stage} />
            ) : stage === 'saved' && receipt ? (
              <EmptyState className="fs-pop-in" icon={<CheckCircle2 className="h-5 w-5" />} title="Saved as an expense" description="The receipt is attached to the transaction."
                action={<><ButtonLink to="/app/transactions" variant="outline">View transactions</ButtonLink><Button onClick={reset}>Scan another</Button></>} />
            ) : ex && receipt ? (
              <div className="fs-rise-in space-y-5">
                <div className="grid gap-3 sm:grid-cols-2">
                  {([['Merchant', ex.merchant, ex.merchant.value], ['Date', ex.date, ex.date.value],
                    ['Total', ex.total, ex.total_minor !== null ? money(ex.total_minor) : null],
                    ['Tax', ex.tax, ex.tax_minor !== null ? money(ex.tax_minor) : null]] as const).map(([label, field, display]) => (
                    <div key={label} className="rounded-lg border border-border p-3">
                      <p className="text-xs text-muted">{label}</p>
                      <p className="mt-0.5 truncate text-sm font-semibold">{display ?? '—'}</p>
                      <div className="mt-1.5"><Confidence field={field} /></div>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-muted">
                  <span>OCR confidence {ex.ocr_confidence}% · {ex.line_count} line(s) read</span>
                  {ex.currency.value && <span>· Currency detected: {ex.currency.value}</span>}
                  {ex.suggested_category.value && <span>· Suggested category: {categoryName(String(ex.suggested_category.value))}</span>}
                  {ex.total.verified_by && <span>· Total cross-checked with {ex.total.verified_by}</span>}
                </div>
                {(ex.warnings.length > 0 || ex.currency_mismatch) && (
                  <ul className="space-y-1 rounded-lg bg-warning-soft px-3 py-2 text-[13px] text-warning">
                    {ex.currency_mismatch && <li>The receipt appears to be in {ex.currency.value}, but your account uses {currency}. Convert the amount before saving — no automatic conversion is done.</li>}
                    {ex.warnings.map((w) => <li key={w}>{w}</li>)}
                  </ul>
                )}
                {ex.line_items.length > 0 && (
                  <details className="rounded-lg border border-border">
                    <summary className="cursor-pointer px-3 py-2 text-[13px] font-medium">Line items ({ex.line_items.length})</summary>
                    <table className="w-full text-[13px]"><tbody className="divide-y divide-border">
                      {ex.line_items.map((li, i) => (
                        <tr key={i}><td className="px-3 py-1.5">{li.description}{li.quantity ? <span className="text-muted"> × {li.quantity}</span> : null}</td>
                          <td className="px-3 py-1.5 text-right tabular">{li.amount}</td></tr>
                      ))}
                    </tbody></table>
                  </details>
                )}
                <details className="rounded-lg border border-border">
                  <summary className="cursor-pointer px-3 py-2 text-[13px] font-medium">Raw text read from the receipt</summary>
                  <pre className="max-h-60 overflow-auto whitespace-pre-wrap border-t border-border bg-surface-2 p-3 text-xs">{ex.raw_text || '(no text detected)'}</pre>
                </details>
                <div className="border-t border-border pt-4">
                  <h3 className="mb-3 text-sm font-semibold">Confirm expense details</h3>
                  <ExpenseForm defaults={defaults} submitLabel="Save expense" onSubmit={confirm} onCancel={reset} />
                </div>
              </div>
            ) : (
              <EmptyState icon={<ScanLine className="h-5 w-5" />} title="No receipt scanned yet" description="Upload an image to extract the merchant, date, total and tax. Clear, well-lit photos work best." />
            )}
          </CardBody>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader title="Recent receipts" />
        <CardBody className="px-0">
          {list.error ? <ErrorState error={list.error} onRetry={list.reload} /> : !list.data ? <div className="px-5"><Skeleton className="h-16" /></div>
            : list.data.items.length === 0 ? <p className="px-5 text-[13px] text-muted">No receipts uploaded yet.</p> : (
              <ul className="divide-y divide-border">
                {list.data.items.map((r) => (
                  <li key={r.id} className="flex flex-wrap items-center gap-3 px-5 py-2.5 text-[13px]">
                    <FileImage className="h-4 w-4 text-muted" aria-hidden />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{r.extracted?.merchant.value ?? 'Receipt'} {r.extracted?.total_minor != null && <span className="tabular text-muted">· {money(r.extracted.total_minor)}</span>}</p>
                      <p className="text-xs text-muted">Uploaded {formatDateTime(r.uploaded_at, timezone)}</p>
                    </div>
                    <Badge tone={r.status === 'confirmed' ? 'success' : r.status === 'failed' ? 'danger' : 'neutral'}>
                      {{ confirmed: 'Saved as expense', processed: 'Awaiting review', uploaded: 'Not processed', failed: 'Processing failed', pending_upload: 'Pending' }[r.status]}
                    </Badge>
                    {r.status !== 'confirmed' && (
                      <Button size="sm" variant="ghost" onClick={async () => {
                        setFile(null); setError(null)
                        try { await process(r.id) } catch (err) { setError(errorMessage(err)); setStage('idle') }
                        list.reload()
                      }}><RotateCcw className="h-3.5 w-3.5" aria-hidden />{r.status === 'processed' ? 'Review' : 'Process'}</Button>
                    )}
                    {r.expense_id && <Link to={`/app/transactions?open=${r.expense_id}`} className="text-xs font-medium text-primary hover:underline">View expense</Link>}
                    <Button size="icon" variant="ghost" aria-label="Delete receipt" onClick={() => setDeleting(r)}><Trash2 className="h-4 w-4" /></Button>
                  </li>
                ))}
              </ul>
            )}
        </CardBody>
      </Card>

      <ConfirmDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)} title="Delete this receipt?"
        description="The image and extracted data are permanently deleted. Any linked expense is kept, without the attachment."
        onConfirm={async () => {
          try {
            await api.del(`/receipts/${deleting!.id}`)
            toast.success('Receipt deleted')
            if (receipt?.id === deleting!.id) reset()
            list.reload()
          } catch (err) {
            toast.error(errorMessage(err))
            throw err
          }
        }} />
    </>
  )
}
