// Single API client used by every page. Changing the backend URL only
// requires VITE_API_BASE_URL; no page builds URLs itself.

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  code: string
  details: { field: string | null; message: string }[] | undefined

  constructor(status: number, code: string, message: string, details?: { field: string | null; message: string }[]) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

type TokenProvider = () => Promise<string | null>
type UnauthorizedHandler = () => void

let tokenProvider: TokenProvider = async () => null
let onUnauthorized: UnauthorizedHandler = () => {}

export function configureAuth(provider: TokenProvider, unauthorized: UnauthorizedHandler) {
  tokenProvider = provider
  onUnauthorized = unauthorized
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  query?: Record<string, string | number | boolean | string[] | null | undefined>
  form?: FormData
  signal?: AbortSignal
  auth?: boolean
  raw?: boolean
}

function buildQuery(query: RequestOptions['query']) {
  if (!query) return ''
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === '') continue
    if (Array.isArray(value)) value.forEach((v) => params.append(key, v))
    else params.append(key, String(value))
  }
  const s = params.toString()
  return s ? `?${s}` : ''
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {}
  if (opts.auth !== false) {
    const token = await tokenProvider()
    if (token) headers.Authorization = `Bearer ${token}`
  }
  let body: BodyInit | undefined
  if (opts.form) body = opts.form
  else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE}/api/v1${path}${buildQuery(opts.query)}`, {
      method: opts.method ?? 'GET',
      headers,
      body,
      signal: opts.signal,
    })
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err
    throw new ApiError(0, 'network_error', 'Cannot reach the server. Check that the backend is running and try again.')
  }

  if (response.status === 204) return undefined as T
  if (opts.raw && response.ok) return (await response.blob()) as T

  let payload: any = null
  const text = await response.text()
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) {
    const err = payload?.error
    // A gateway/proxy error without our error envelope means the API itself is unreachable.
    if (!err && [502, 503, 504].includes(response.status)) {
      throw new ApiError(0, 'network_error', 'Cannot reach the server. Check that the backend is running and try again.')
    }
    const apiError = new ApiError(
      response.status,
      err?.code ?? 'http_error',
      err?.message ?? (response.status >= 500 ? 'The server encountered an error. Please try again.' : `Request failed (${response.status}).`),
      err?.details,
    )
    if (response.status === 401 && opts.auth !== false) onUnauthorized()
    throw apiError
  }
  return payload as T
}

export const api = {
  get: <T>(path: string, query?: RequestOptions['query'], signal?: AbortSignal) => request<T>(path, { query, signal }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  del: <T = void>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: 'POST', form }),
  blob: (path: string) => request<Blob>(path, { raw: true }),
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) return err.message
  return 'Something went wrong.'
}

/** Map API field errors onto react-hook-form fields. */
export function fieldErrors(err: unknown): Record<string, string> {
  const out: Record<string, string> = {}
  if (err instanceof ApiError && err.details) {
    for (const d of err.details) if (d.field) out[d.field] = d.message
  }
  return out
}
