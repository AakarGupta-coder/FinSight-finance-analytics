import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { Bot, MessageSquare, Send, Trash2, User } from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'
import { formatDate } from '../lib/format'
import { useDocumentTitle } from '../lib/hooks'
import type { AssistantReply } from '../lib/types'
import { Badge, Button, Card, CardHeader, Input, PageHeader } from '../components/ui/primitives'
import { cn } from '../lib/utils'

interface Message { id: number; role: 'user' | 'assistant'; text: string; reply?: AssistantReply; error?: boolean }

const STARTERS = [
  'How much did I spend this month?',
  'How much did I spend on food last month?',
  'Which category increased the most?',
  'What is my remaining monthly budget?',
  'Am I approaching my monthly budget limit?',
  'Which transactions were unusually large?',
  'How much could I save by reducing shopping by 20%?',
  'How much do I need to save each month to reach my goal?',
]

function ReplyData({ reply }: { reply: AssistantReply }) {
  const { money } = useAppData()
  const d = reply.data
  if (!d) return null
  if ((d.kind === 'transactions') && Array.isArray(d.rows) && d.rows.length) {
    return (
      <ul className="mt-2 divide-y divide-border rounded-lg border border-border bg-surface text-[13px]">
        {d.rows.map((r: any) => (
          <li key={r.id ?? r.alert_id} className="flex items-start justify-between gap-3 px-3 py-2">
            <div className="min-w-0">
              <p className="truncate font-medium">{r.description}</p>
              <p className="text-xs text-muted">{formatDate(r.date)} · {r.category_name}{r.reason ? ` · ${r.reason}` : ''}</p>
            </div>
            <span className="shrink-0 font-semibold tabular">{money(r.amount_minor)}</span>
          </li>
        ))}
      </ul>
    )
  }
  if ((d.kind === 'breakdown' || d.kind === 'comparison') && Array.isArray(d.rows)) {
    return (
      <table className="mt-2 w-full rounded-lg border border-border bg-surface text-[13px]">
        <tbody className="divide-y divide-border">
          {d.rows.slice(0, 6).map((r: any) => (
            <tr key={r.category}>
              <td className="px-3 py-1.5">{r.category_name}</td>
              {d.kind === 'breakdown'
                ? <td className="px-3 py-1.5 text-right tabular">{money(r.amount_minor)} <span className="text-muted">· {r.share_pct}%</span></td>
                : <td className="px-3 py-1.5 text-right tabular">{money(r.previous_minor)} → {money(r.current_minor)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    )
  }
  return null
}

export default function AssistantPage() {
  useDocumentTitle('Assistant')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const nextId = useRef(1)

  useEffect(() => {
    // Block body: scrollIntoView may return a Promise, which must not be used as an effect cleanup.
    void endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy])

  const ask = async (question: string) => {
    const q = question.trim()
    if (!q || busy) return
    setInput('')
    setMessages((m) => [...m, { id: nextId.current++, role: 'user', text: q }])
    setBusy(true)
    try {
      const reply = await api.post<AssistantReply>('/assistant/query', { question: q.slice(0, 500) })
      setMessages((m) => [...m, { id: nextId.current++, role: 'assistant', text: reply.answer, reply }])
    } catch (err) {
      setMessages((m) => [...m, { id: nextId.current++, role: 'assistant', text: errorMessage(err), error: true }])
    } finally {
      setBusy(false)
    }
  }

  // Follow-ups come from the latest reply; the full starter list lives in the side panel.
  const last = [...messages].reverse().find((m) => m.reply)?.reply
  const followUps = last?.suggestions ?? []

  return (
    <>
      <PageHeader title="Finance assistant" description="Ask about your spending, budgets and goals. Answers are calculated from your own records — no external AI service is used."
        actions={messages.length > 0 && <Button variant="ghost" onClick={() => setMessages([])}><Trash2 className="h-4 w-4" aria-hidden />Clear chat</Button>} />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="flex h-[calc(100vh-11rem)] min-h-[440px] flex-col">
          <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5" aria-live="polite" aria-label="Conversation">
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center py-6 text-center">
                <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface-3 text-emerald"><Bot className="h-5 w-5" aria-hidden /></div>
                <h2 className="mt-3 text-sm font-medium">What would you like to know?</h2>
                <p className="mt-1 max-w-sm text-[12.5px] text-muted">Type a question below, or pick one from <span className="xl:hidden">the list under the chat</span><span className="hidden xl:inline">the list on the right</span>.</p>
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={cn('fs-message flex gap-3', m.role === 'user' && 'flex-row-reverse')}
                style={{ transformOrigin: m.role === 'user' ? 'right bottom' : 'left bottom' }}>
                <div className={cn('flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border', m.role === 'user' ? 'bg-surface-3 text-text-2' : 'bg-primary-soft text-accent')} aria-hidden>
                  {m.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>
                <div className={cn('max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[13.5px] leading-relaxed',
                  m.role === 'user' ? 'rounded-tr-md bg-primary text-primary-fg' : m.error ? 'rounded-tl-md bg-danger-soft text-danger' : 'rounded-tl-md border border-border bg-surface-2 text-text')}>
                  <span className="sr-only">{m.role === 'user' ? 'You said:' : 'Assistant:'}</span>
                  <p>{m.text}</p>
                  {m.reply && <ReplyData reply={m.reply} />}
                  {m.reply?.period && <p className="mt-1.5 text-xs text-muted">Period: {m.reply.period.label} ({formatDate(m.reply.period.start)} – {formatDate(m.reply.period.end)})</p>}
                  {m.reply?.intent === 'simulate_saving' && <Link to="/app/simulator" className="mt-1.5 inline-block text-xs font-medium text-accent hover:underline">Open the simulator →</Link>}
                  {m.reply?.needs_clarification && <Badge tone="info" className="mt-2">Needs more detail</Badge>}
                </div>
              </div>
            ))}
            {busy && <div className="fs-message flex gap-3" role="status"><div className="flex h-7 w-7 items-center justify-center rounded-full border border-border bg-primary-soft text-accent"><Bot className="h-4 w-4" aria-hidden /></div><div className="flex items-center gap-2 rounded-xl bg-surface-2 px-3.5 py-2.5 text-[13px] text-muted">Calculating<span className="fs-typing tracking-[0.15em]" aria-hidden><span>.</span><span>.</span><span>.</span></span></div></div>}
            <div ref={endRef} />
          </div>
          <div className="border-t border-border p-3">
            {followUps.length > 0 && (
              <div className="mb-2 flex gap-2 overflow-x-auto pb-1" aria-label="Suggested follow-up questions">
                {followUps.map((q) => <button key={q} type="button" onClick={() => ask(q)} className="shrink-0 rounded-full border border-border bg-surface-2 px-2.5 py-1 text-xs text-text-2 hover:border-emerald hover:text-text">{q}</button>)}
              </div>
            )}
            <form onSubmit={(e) => { e.preventDefault(); void ask(input) }} className="flex gap-2">
              <Input aria-label="Ask a question" placeholder="e.g. How much did I spend on transport in September?" value={input} maxLength={500} onChange={(e) => setInput(e.target.value)} />
              <Button type="submit" disabled={!input.trim()} loading={busy} aria-label="Send"><Send className="h-4 w-4" aria-hidden /></Button>
            </form>
            <p className="mt-2 text-xs text-muted">Automated summaries of your records, not financial advice. Conversation history is kept only in this tab.</p>
          </div>
        </Card>
        <Card className="self-start">
          <CardHeader title="Questions you can ask" description="Spending, categories, budgets, anomalies, savings and goals" />
          <ul className="space-y-1 px-3 pb-3">
            {STARTERS.map((q) => (
              <li key={q}>
                <button type="button" onClick={() => ask(q)} disabled={busy}
                  className="flex w-full items-center gap-2 rounded-[10px] px-2.5 py-2 text-left text-[12.5px] text-text-2 transition-colors hover:bg-surface-2 hover:text-text disabled:opacity-50">
                  <MessageSquare className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden />{q}
                </button>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}
