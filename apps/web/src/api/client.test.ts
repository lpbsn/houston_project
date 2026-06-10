import { afterEach, describe, expect, it, vi } from 'vitest'

import { clearApiClientAuth, configureApiClientAuth, withAuthRetry } from './client'

describe('withAuthRetry', () => {
  afterEach(() => {
    clearApiClientAuth()
  })

  it('returns the first result when status is not 401', async () => {
    const execute = vi.fn(async () => ({
      response: new Response(null, { status: 200 }),
    }))

    const result = await withAuthRetry(execute)

    expect(result.response.status).toBe(200)
    expect(execute).toHaveBeenCalledTimes(1)
  })

  it('refreshes and retries once after 401', async () => {
    configureApiClientAuth({
      getAccessToken: () => 'stale-token',
      refreshAccessToken: vi.fn(async () => 'fresh-token'),
      clearAuth: vi.fn(),
    })

    const execute = vi
      .fn()
      .mockResolvedValueOnce({ response: new Response(null, { status: 401 }) })
      .mockResolvedValueOnce({ response: new Response(null, { status: 200 }) })

    const result = await withAuthRetry(execute)

    expect(execute).toHaveBeenCalledTimes(2)
    expect(execute.mock.calls[0]?.[0]).toBe('stale-token')
    expect(execute.mock.calls[1]?.[0]).toBe('fresh-token')
    expect(result.response.status).toBe(200)
  })

  it('clears auth when refresh fails after 401', async () => {
    const clearAuth = vi.fn()
    configureApiClientAuth({
      getAccessToken: () => 'stale-token',
      refreshAccessToken: vi.fn(async () => null),
      clearAuth,
    })

    const execute = vi.fn(async () => ({
      response: new Response(null, { status: 401 }),
    }))

    const result = await withAuthRetry(execute)

    expect(clearAuth).toHaveBeenCalledTimes(1)
    expect(execute).toHaveBeenCalledTimes(1)
    expect(result.response.status).toBe(401)
  })

  it('clears auth when retry still returns 401', async () => {
    const clearAuth = vi.fn()
    configureApiClientAuth({
      getAccessToken: () => 'stale-token',
      refreshAccessToken: vi.fn(async () => 'fresh-token'),
      clearAuth,
    })

    const execute = vi.fn(async () => ({
      response: new Response(null, { status: 401 }),
    }))

    await withAuthRetry(execute)

    expect(clearAuth).toHaveBeenCalledTimes(1)
    expect(execute).toHaveBeenCalledTimes(2)
  })
})
