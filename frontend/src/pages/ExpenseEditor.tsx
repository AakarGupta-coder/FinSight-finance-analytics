import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { ScanLine, Trash2 } from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'
import { useApi, useDocumentTitle } from '../lib/hooks'
import type { Expense, ExpenseMutation } from '../lib/types'
import { Button, ButtonLink, Card, CardBody, ErrorState, PageHeader, Spinner } from '../components/ui/primitives'
import { ConfirmDialog } from '../components/ui/dialog'
import { ExpenseForm, type ExpensePayload } from '../components/ExpenseForm'
import { announceMutationEffects } from '../components/feedback'

export default function ExpenseEditorPage() {
  const { id } = useParams()
  const editing = !!id
  useDocumentTitle(editing ? 'Edit expense' : 'Add expense')
  const navigate = useNavigate()
  const { currency, money } = useAppData()
  const { data: existing, error, reload } = useApi<Expense>(editing ? `/expenses/${id}` : null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const save = async (payload: ExpensePayload) => {
    const body = { ...payload, receipt_id: existing?.receipt_id ?? null }
    const result = editing
      ? await api.put<ExpenseMutation>(`/expenses/${id}`, body)
      : await api.post<ExpenseMutation>('/expenses', body)
    toast.success(editing ? 'Expense updated' : 'Expense added', { description: `${result.expense.description} · ${money(result.expense.amount_minor)}` })
    announceMutationEffects(result, currency)
    navigate('/app/transactions')
  }

  if (editing && error) return <Card><ErrorState error={error} onRetry={reload} /></Card>
  if (editing && !existing) return <Spinner label="Loading transaction" />

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title={editing ? 'Edit expense' : 'Add expense'}
        description={editing ? 'Changes update budgets, analytics and insights immediately.' : 'Record a new expense. Amounts are stored exactly, without rounding.'}
        actions={!editing && <ButtonLink to="/app/receipts" variant="outline"><ScanLine className="h-4 w-4" aria-hidden />Scan a receipt instead</ButtonLink>} />
      <Card>
        <CardBody className="pt-5">
          <ExpenseForm
            defaults={existing ?? undefined}
            submitLabel={editing ? 'Save changes' : 'Add expense'}
            onSubmit={save}
            onCancel={() => navigate(-1)}
            footerExtra={editing && <Button variant="ghost" className="mr-auto text-danger" onClick={() => setConfirmDelete(true)}><Trash2 className="h-4 w-4" aria-hidden />Delete</Button>}
          />
        </CardBody>
      </Card>
      {existing && (
        <ConfirmDialog open={confirmDelete} onOpenChange={setConfirmDelete} title="Delete this transaction?"
          description={`“${existing.description}” (${money(existing.amount_minor)}) will be permanently removed.`}
          onConfirm={async () => {
            try {
              await api.del(`/expenses/${existing.id}`)
              toast.success('Transaction deleted')
              navigate('/app/transactions')
            } catch (err) {
              toast.error(errorMessage(err))
              throw err
            }
          }} />
      )}
    </div>
  )
}
