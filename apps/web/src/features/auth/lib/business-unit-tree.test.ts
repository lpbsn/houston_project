import { beforeEach, describe, expect, it, vi } from 'vitest'

const { withAuthRetryMock, apiClientGetMock } = vi.hoisted(() => ({
  withAuthRetryMock: vi.fn(),
  apiClientGetMock: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  withAuthRetry: (...args: unknown[]) => withAuthRetryMock(...args),
  apiClient: {
    GET: (...args: unknown[]) => apiClientGetMock(...args),
  },
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
    withAuthRetryMock.mockImplementation(async (execute: (token: string | null) => Promise<unknown>) =>
      execute('access-token'),
    )
    apiClientGetMock.mockResolvedValue({
      data: treePayload,
      error: undefined,
      response: { status: 200, ok: true },
    })
  })

  it('loads the tree through apiClient with bearer auth', async () => {
    const result = await fetchBusinessUnitTree('est-1')

    expect(withAuthRetryMock).toHaveBeenCalledWith(expect.any(Function), { refreshable: true })
    expect(apiClientGetMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/business-units/',
      {
        params: {
          path: { establishment_id: 'est-1' },
        },
        headers: {
          Authorization: 'Bearer access-token',
        },
      },
    )
    expect(result).toEqual(treePayload)
  })

  it('passes include_inactive when requested', async () => {
    await fetchBusinessUnitTree('est-1', { includeInactive: true })

    expect(apiClientGetMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/business-units/',
      expect.objectContaining({
        params: {
          path: { establishment_id: 'est-1' },
          query: { include_inactive: true },
        },
      }),
    )
  })

  it('throws AuthApiError when the response is not ok', async () => {
    apiClientGetMock.mockResolvedValue({
      data: undefined,
      error: { detail: 'forbidden' },
      response: { status: 403, ok: false },
    })

    await expect(fetchBusinessUnitTree('est-1')).rejects.toMatchObject({
      name: 'AuthApiError',
      status: 403,
      message: 'Business unit tree could not be loaded.',
    })
  })

  it('passes the access token from withAuthRetry into the Authorization header', async () => {
    let capturedToken: string | null = null
    withAuthRetryMock.mockImplementationOnce(
      async (execute: (token: string | null) => Promise<unknown>) => {
        capturedToken = 'token-from-retry'
        return execute(capturedToken)
      },
    )

    await fetchBusinessUnitTree('est-1')

    expect(capturedToken).toBe('token-from-retry')
    expect(apiClientGetMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/business-units/',
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer token-from-retry',
        },
      }),
    )
  })
})

describe('AuthApiError', () => {
  it('is thrown for failed tree loads', () => {
    const error = new AuthApiError('Business unit tree could not be loaded.', 401)
    expect(error).toBeInstanceOf(Error)
    expect(error.name).toBe('AuthApiError')
  })
})
