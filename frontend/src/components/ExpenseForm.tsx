import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAppData } from '../lib/appData'
import { fieldErrors, errorMessage } from '../lib/api'
import { minorToInput, parseMoneyToMinor } from '../lib/format'
import { Button, Field, Input, Select, Textarea } from './ui/primitives'

export interface ExpensePayload {
  amount_minor: number
  date: string
  category: string
  description: string
  merchant: string | null
  payment_method: string
  notes: string | null
}

export interface ExpenseFormDefaults {
  amount_minor?: number | null
  date?: string | null
  category?: string | null
  description?: string | null
  merchant?: string | null
  payment_method?: string | null
  notes?: string | null
}

function makeSchema(currency: string, today: string) {
  return z.object({
    amount: z.string().trim().min(1, 'Enter an amount').refine((v) => {
      const m = parseMoneyToMinor(v, currency)
      return m !== null && m > 0
    }, 'Enter a positive amount with at most 2 decimals'),
    date: z.string().min(1, 'Choose a date').refine((v) => v <= today, 'Date cannot be in the future').refine((v) => v >= '2000-01-01', 'Date is too far in the past'),
    category: z.string().min(1, 'Choose a category'),
    description: z.string().trim().min(1, 'Enter a description').max(120, 'Keep it under 120 characters'),
    merchant: z.string().trim().max(80, 'Keep it under 80 characters'),
    payment_method: z.string().min(1, 'Choose a payment method'),
    notes: z.string().trim().max(500, 'Keep it under 500 characters'),
  })
}

type Values = z.infer<ReturnType<typeof makeSchema>>

export function ExpenseForm({ defaults, submitLabel, onSubmit, onCancel, footerExtra }: {
  defaults?: ExpenseFormDefaults
  submitLabel: string
  onSubmit: (payload: ExpensePayload) => Promise<void>
  onCancel?: () => void
  footerExtra?: React.ReactNode
}) {
  const { currency, today, reference } = useAppData()
  const toValues = (d?: ExpenseFormDefaults): Values => ({
    amount: d?.amount_minor ? minorToInput(d.amount_minor, currency) : '',
    date: d?.date ?? today,
    category: d?.category ?? '',
    description: d?.description ?? '',
    merchant: d?.merchant ?? '',
    payment_method: d?.payment_method ?? 'upi',
    notes: d?.notes ?? '',
  })
  const { register, handleSubmit, reset, setError, formState: { errors, isSubmitting } } = useForm<Values>({
    resolver: zodResolver(makeSchema(currency, today)),
    defaultValues: toValues(defaults),
  })

  useEffect(() => {
    reset(toValues(defaults))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(defaults)])

  const submit = handleSubmit(async (v) => {
    try {
      await onSubmit({
        amount_minor: parseMoneyToMinor(v.amount, currency)!,
        date: v.date,
        category: v.category,
        description: v.description,
        merchant: v.merchant || null,
        payment_method: v.payment_method,
        notes: v.notes || null,
      })
    } catch (err) {
      const fields = fieldErrors(err)
      const map: Record<string, keyof Values> = { amount_minor: 'amount' }
      Object.entries(fields).forEach(([k, msg]) => setError((map[k] ?? k) as keyof Values, { message: msg }))
      if (!Object.keys(fields).length) setError('root', { message: errorMessage(err) })
    }
  })

  return (
    <form onSubmit={submit} noValidate className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={`Amount (${currency})`} htmlFor="amount" error={errors.amount?.message} required>
          <Input id="amount" inputMode="decimal" placeholder="0.00" autoComplete="off" aria-invalid={!!errors.amount} {...register('amount')} />
        </Field>
        <Field label="Date" htmlFor="date" error={errors.date?.message} required>
          <Input id="date" type="date" max={today} aria-invalid={!!errors.date} {...register('date')} />
        </Field>
        <Field label="Category" htmlFor="category" error={errors.category?.message} required>
          <Select id="category" aria-invalid={!!errors.category} {...register('category')}>
            <option value="">Select a category</option>
            {reference?.categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </Field>
        <Field label="Payment method" htmlFor="payment_method" error={errors.payment_method?.message} required>
          <Select id="payment_method" {...register('payment_method')}>
            {reference?.payment_methods.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
        </Field>
        <Field label="Description" htmlFor="description" error={errors.description?.message} required className="sm:col-span-2">
          <Input id="description" placeholder="e.g. Weekly groceries" aria-invalid={!!errors.description} {...register('description')} />
        </Field>
        <Field label="Merchant" htmlFor="merchant" error={errors.merchant?.message} hint="Optional">
          <Input id="merchant" placeholder="e.g. FreshMart" {...register('merchant')} />
        </Field>
        <Field label="Notes" htmlFor="notes" error={errors.notes?.message} hint="Optional" className="sm:col-span-2">
          <Textarea id="notes" rows={3} {...register('notes')} />
        </Field>
      </div>
      {errors.root?.message && <p role="alert" className="rounded-lg bg-danger-soft px-3 py-2 text-[13px] text-danger">{errors.root.message}</p>}
      <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
        {footerExtra}
        {onCancel && <Button variant="outline" onClick={onCancel}>Cancel</Button>}
        <Button type="submit" loading={isSubmitting}>{submitLabel}</Button>
      </div>
    </form>
  )
}
