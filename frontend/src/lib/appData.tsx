import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from './api'
import { money as formatMoney, todayIn } from './format'
import type { Me, Reference } from './types'

interface AppData {
  me: Me | null
  reference: Reference | null
  loading: boolean
  error: unknown
  reload: () => Promise<void>
  currency: string
  timezone: string
  today: string
  categoryName: (id: string) => string
  paymentMethodName: (id: string) => string
  money: (minor: number | null | undefined, opts?: { compact?: boolean; fraction?: boolean; round?: boolean }) => string
}

const Ctx = createContext<AppData | null>(null)

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [reference, setReference] = useState<Reference | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)

  const reload = useCallback(async () => {
    try {
      setError(null)
      const [m, r] = await Promise.all([api.get<Me>('/me'), api.get<Reference>('/reference')])
      setMe(m)
      setReference(r)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const value = useMemo<AppData>(() => {
    const currency = me?.preferences.currency ?? 'INR'
    const timezone = me?.preferences.timezone ?? 'Asia/Kolkata'
    const cats = new Map((reference?.categories ?? me?.preferences.categories ?? []).map((c) => [c.id, c.name]))
    const methods = new Map((reference?.payment_methods ?? []).map((p) => [p.id, p.name]))
    return {
      me, reference, loading, error, reload, currency, timezone,
      today: todayIn(timezone),
      categoryName: (id) => cats.get(id) ?? id,
      paymentMethodName: (id) => methods.get(id) ?? id,
      money: (minor, opts) => formatMoney(minor, currency, opts),
    }
  }, [me, reference, loading, error, reload])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAppData() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAppData must be used within AppDataProvider')
  return ctx
}
