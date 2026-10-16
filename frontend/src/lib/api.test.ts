import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, configureAuth, fieldErrors, request } from './api'

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue(new Response(body === undefined ? null : JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => {
  vi.unstubAllGlobals()
  configureAuth(async () => null, () => {})
})

describe('request', () => {
  it('attaches the bearer token and builds query strings', async () => {
    const fetchFn = mockFetch(200, { ok: true })
    configureAuth(async () => 'token-123', () => {})
    await request('/expenses', { query: { category: ['food', 'travel'], page: 2, search: '' } })
    const [url, init] = fetchFn.mock.calls[0]
    expect(url).toBe('/api/v1/expenses?category=food&category=travel&page=2')
    expect(init.headers.Authorization).toBe('Bearer token-123')
  })

  it('raises ApiError with field details and calls the 401 handler', async () => {
    const onUnauthorized = vi.fn()
    configureAuth(async () => 'expired', onUnauthorized)
    mockFetch(401, { error: { code: 'token_expired', message: 'Session expired' } })
    await expect(request('/me')).rejects.toMatchObject({ status: 401, code: 'token_expired' })
    expect(onUnauthorized).toHaveBeenCalled()

    mockFetch(422, { error: { code: 'validation_error', message: 'Bad', details: [{ field: 'amount_minor', message: 'Too small' }] } })
    try {
      await request('/expenses', { method: 'POST', body: {} })
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect(fieldErrors(err)).toEqual({ amount_minor: 'Too small' })
    }
  })

  it('reports network failures clearly instead of returning fake data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(request('/dashboard')).rejects.toMatchObject({ code: 'network_error' })
  })

  it('treats a bare gateway error (backend down behind a proxy) as unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 502 })))
    await expect(request('/dashboard')).rejects.toMatchObject({ code: 'network_error' })
    mockFetch(503, { error: { code: 'ocr_unavailable', message: 'OCR missing' } })
    await expect(request('/receipts/x/process', { method: 'POST' })).rejects.toMatchObject({ code: 'ocr_unavailable' })
  })
})
