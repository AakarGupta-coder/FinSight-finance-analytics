import { useCallback, useEffect, useRef, useState } from 'react'
import { request } from './api'

type Query = Record<string, string | number | boolean | string[] | null | undefined>

/** Fetch a resource and expose loading / error / reload. Never substitutes fake data on failure. */
export function useApi<T>(path: string | null, query?: Query) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState<boolean>(!!path)
  const [nonce, setNonce] = useState(0)
  const queryKey = JSON.stringify(query ?? {})
  const first = useRef(true)

  useEffect(() => {
    if (!path) {
      setLoading(false)
      return
    }
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    request<T>(path, { query: JSON.parse(queryKey), signal: controller.signal })
      .then((result) => {
        setData(result)
        first.current = false
      })
      .catch((err) => {
        if ((err as Error).name !== 'AbortError') setError(err)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [path, queryKey, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { data, error, loading, reload, setData, initialLoading: loading && data === null }
}

export function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(id)
  }, [value, delay])
  return debounced
}

export function useDocumentTitle(title: string) {
  useEffect(() => {
    // Pages read "Dashboard · FinSight"; the landing page uses the full product title.
    document.title = title ? `${title} · FinSight` : 'FinSight — Personal Finance Intelligence'
  }, [title])
}
