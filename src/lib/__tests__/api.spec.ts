import { describe, it, expect, vi, afterEach } from 'vitest'

import { ApiError, checkCode, getConsent } from '@/lib/api'

afterEach(() => vi.restoreAllMocks())

describe('api client', () => {
  it('checkCode POSTs the code in the body and returns validity', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => ({ valid: true }) })
    vi.stubGlobal('fetch', fetchMock)

    const result = await checkCode('MDAP-2026-001')

    expect(result.valid).toBe(true)
    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(String(url)).toContain('/api/codes/validate')
    expect(init?.method).toBe('POST')
    expect(JSON.parse(init?.body as string)).toEqual({ code: 'MDAP-2026-001' })
  })

  it('checkCode throws ApiError with the status on a non-ok response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 429, json: async () => ({ detail: 'slow' }) }),
    )

    await expect(checkCode('whatever')).rejects.toMatchObject({ status: 429 })
    await expect(checkCode('whatever')).rejects.toBeInstanceOf(ApiError)
  })

  it('getConsent returns the version and text', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ version: 'v1.0', text: 'T' }) }),
    )

    expect(await getConsent()).toEqual({ version: 'v1.0', text: 'T' })
  })
})
