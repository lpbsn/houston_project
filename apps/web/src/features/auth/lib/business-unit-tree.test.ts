import { beforeEach, describe, expect, it, vi } from 'vitest'

const withAuthRetryMock = vi.fn()
const ensureCsrfTokenMock = vi.fn()

vi.mock('@/api/client', () => ({
  withAuthRetry: (...args: unknown[]) => withAuthRetryMock(...args),
}))

vi.mock('@/features/auth/csrf', () => ({
  ensureCsrfToken: () => ensureCsrfTokenMock(),
}))

import { AuthApiError, businessUnitTreeQueryKey, fetchBusinessUnitTree } from '@/features/auth/api'

const treePayload = {
  establishment_id: 'est-1',
  establishment_name: 'Test establishment',
  business_units: [],
}

describe('businessUnitTreeQueryKey', () => {
  it('returns a stable query key shape', () => {
    expect(businessUnitTreeQueryKey('est-1')).toEqual(['workspace', 'business-units', 'est-1'])
  })
})

describe('fetchBusinessUnitTree', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ensureCsrfTokenMock.mockResolvedValue('csrf-token')
    withAuthRetryMock.mockImplementation(async (execute: (token: string | null) => Promise<unknown>) =>
      execute('access-token'),
    )
  })

  it('loads the tree through withAuthRetry with CSRF, credentials, and bearer auth', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => treePayload,
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await fetchBusinessUnitTree('est-1')

    expect(ensureCsrfTokenMock).toHaveBeenCalledOnce()
    expect(withAuthRetryMock).toHaveBeenCalledWith(expect.any(Function), { refreshable: true })
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/establishments/est-1/business-units/', {
      credentials: 'include',
      headers: {
        Authorization: 'Bearer access-token',
        'X-CSRFToken': 'csrf-token',
      },
    })
    expect(result).toEqual(treePayload)

    vi.unstubAllGlobals()
  })

  it('throws AuthApiError when the response is not ok', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({}),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchBusinessUnitTree('est-1')).rejects.toMatchObject({
      name: 'AuthApiError',
      status: 403,
      message: 'Business unit tree could not be loaded.',
    })

    vi.unstubAllGlobals()
  })

  it('passes the access token from withAuthRetry into the fetch Authorization header', async () => {
    let capturedToken: string | null = null
    withAuthRetryMock.mockImplementationOnce(
      async (execute: (token: string | null) => Promise<unknown>) => {
        capturedToken = 'token-from-retry'
        return execute(capturedToken)
      },
    )

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => treePayload,
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchBusinessUnitTree('est-1')

    expect(capturedToken).toBe('token-from-retry')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer token-from-retry',
        }),
      }),
    )

    vi.unstubAllGlobals()
  })
})

describe('AuthApiError', () => {
  it('is thrown for failed tree loads', () => {
    const error = new AuthApiError('Business unit tree could not be loaded.', 401)
    expect(error).toBeInstanceOf(Error)
    expect(error.name).toBe('AuthApiError')
  })
})
