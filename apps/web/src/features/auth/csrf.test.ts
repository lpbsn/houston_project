import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { apiClientGetMock } = vi.hoisted(() => ({
  apiClientGetMock: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  apiClient: {
    GET: (...args: unknown[]) => apiClientGetMock(...args),
  },
}))

import { clearCsrfTokenCache, ensureCsrfToken } from './csrf'

describe('ensureCsrfToken', () => {
  beforeEach(() => {
    clearCsrfTokenCache()
    apiClientGetMock.mockReset()
  })

  afterEach(() => {
    clearCsrfTokenCache()
  })

  it('reads csrf_token from JSON and caches it in memory', async () => {
    apiClientGetMock.mockResolvedValue({
      data: { detail: 'CSRF cookie set.', csrf_token: 'token-from-json' },
      error: undefined,
    })

    await expect(ensureCsrfToken()).resolves.toBe('token-from-json')
    await expect(ensureCsrfToken()).resolves.toBe('token-from-json')
    expect(apiClientGetMock).toHaveBeenCalledTimes(1)
    expect(apiClientGetMock).toHaveBeenCalledWith('/api/v1/auth/csrf/', {
      credentials: 'include',
    })
  })

  it('fails when the JSON response has no csrf_token', async () => {
    apiClientGetMock.mockResolvedValue({
      data: { detail: 'CSRF cookie set.' },
      error: undefined,
    })

    await expect(ensureCsrfToken()).rejects.toThrow('Unable to initialize CSRF protection.')
  })
})
