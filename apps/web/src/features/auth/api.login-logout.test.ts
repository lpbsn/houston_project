import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { queryClient } from '@/lib/query-client'
import {
  acceptInvitationSession,
  clearAuthState,
  confirmPasswordReset,
  deleteAccount,
  login,
  logout,
  refreshAccessToken,
} from '@/features/auth/api'
import { __resetObservationComposeDraftStoreForTests } from '@/features/observations/lib/observation-compose-draft-store'
import { resetSuccessToastsForTests } from '@/lib/success-toast'
import {
  clearBodyRefreshTokenStoreConfiguration,
  configureBodyRefreshTokenStore,
} from './refresh-token-transport'
import { bootstrapPayload, bootstrapQueryKey, deferred } from './api.test-setup'

const {
  withAuthRetryMock,
  apiClientGetMock,
  apiClientPostMock,
  clearAccessTokenMock,
  setAccessTokenMock,
  getAccessTokenMock,
  runNativePushBeforeLogoutMock,
  clearPendingNativeDeepLinkMock,
} = vi.hoisted(() => ({
  withAuthRetryMock: vi.fn(),
  apiClientGetMock: vi.fn(),
  apiClientPostMock: vi.fn(),
  clearAccessTokenMock: vi.fn(),
  setAccessTokenMock: vi.fn(),
  getAccessTokenMock: vi.fn(),
  runNativePushBeforeLogoutMock: vi.fn(async () => undefined),
  clearPendingNativeDeepLinkMock: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  apiClient: {
    GET: (...args: unknown[]) => apiClientGetMock(...args),
    POST: (...args: unknown[]) => apiClientPostMock(...args),
  },
  withAuthRetry: (...args: unknown[]) => withAuthRetryMock(...args),
}))

vi.mock('./csrf', () => ({
  clearCsrfTokenCache: vi.fn(),
  ensureCsrfToken: vi.fn(async () => 'csrf-token'),
}))

vi.mock('./session', () => ({
  clearAccessToken: () => clearAccessTokenMock(),
  getAccessToken: () => getAccessTokenMock(),
  setAccessToken: (token: string) => setAccessTokenMock(token),
}))

vi.mock('@/lib/native-push-session', () => ({
  runNativePushBeforeLogout: () => runNativePushBeforeLogoutMock(),
}))

vi.mock('@/lib/native-deep-link-session', () => ({
  clearPendingNativeDeepLink: () => clearPendingNativeDeepLinkMock(),
}))

function resetAuthApiTest() {
  vi.clearAllMocks()
  queryClient.clear()
  resetSuccessToastsForTests()
  withAuthRetryMock.mockImplementation(async (execute: (token: string | null) => Promise<unknown>) =>
    execute('access-token'),
  )
}

function cleanupAuthApiTest() {
  __resetObservationComposeDraftStoreForTests()
  clearBodyRefreshTokenStoreConfiguration()
  vi.unstubAllEnvs()
}

describe('auth api login logout', () => {
  beforeEach(() => {
    resetAuthApiTest()
  })

  afterEach(() => {
    cleanupAuthApiTest()
  })

  it('omits cookies and persists body refresh before installing access state', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    const events: string[] = []
    const store = {
      read: vi.fn(async () => null),
      write: vi.fn(async () => {
        events.push('refresh-persisted')
      }),
      clear: vi.fn(async () => undefined),
    }
    configureBodyRefreshTokenStore(store)
    setAccessTokenMock.mockImplementationOnce(() => {
      expect(queryClient.getQueryData(bootstrapQueryKey)).toBeUndefined()
      events.push('access-installed')
    })
    apiClientPostMock.mockResolvedValueOnce({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        refresh_token: 'native-refresh',
        refresh_token_expires_at: '2026-09-15T00:00:00Z',
      },
      error: undefined,
    })

    await login({ email: 'owner@example.com', password: 'secret' })

    expect(apiClientPostMock).toHaveBeenCalledWith(
      '/api/v1/auth/login/',
      expect.objectContaining({
        body: expect.objectContaining({ refresh_token_transport: 'body' }),
        credentials: 'omit',
        headers: undefined,
      }),
    )
    expect(events).toEqual(['refresh-persisted', 'access-installed'])
    expect(queryClient.getQueryData(bootstrapQueryKey)).toBeDefined()
  })

  it('fails closed and revokes best-effort when body refresh persistence fails', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    const cleanupResponse = deferred<{
      response: { status: number }
      data: undefined
      error: undefined
    }>()
    const store = {
      read: vi.fn(async () => null),
      write: vi.fn(async () => {
        throw new Error('secure store unavailable')
      }),
      clear: vi.fn(async () => undefined),
    }
    configureBodyRefreshTokenStore(store)
    apiClientPostMock
      .mockResolvedValueOnce({
        response: { status: 200 },
        data: {
          ...bootstrapPayload,
          access_token: 'transient-access',
          refresh_token: 'transient-refresh',
          refresh_token_expires_at: '2026-09-15T00:00:00Z',
        },
        error: undefined,
      })
      .mockImplementationOnce(() => cleanupResponse.promise)

    const loginPromise = login({ email: 'owner@example.com', password: 'secret' })
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(2)
    })
    expect(clearAccessTokenMock).toHaveBeenCalled()
    expect(queryClient.getQueryData(bootstrapQueryKey)).toBeUndefined()

    cleanupResponse.resolve({
      response: { status: 204 },
      data: undefined,
      error: undefined,
    })
    await expect(loginPromise).rejects.toThrow(/could not be persisted/)

    expect(apiClientPostMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/auth/logout/',
      expect.objectContaining({
        body: {
          refresh_token_transport: 'body',
          refresh_token: 'transient-refresh',
        },
        credentials: 'omit',
        headers: { Authorization: 'Bearer transient-access' },
      }),
    )
    expect(store.clear).toHaveBeenCalledOnce()
    expect(setAccessTokenMock).not.toHaveBeenCalled()
    expect(queryClient.getQueryData(bootstrapQueryKey)).toBeUndefined()
  })

  it('sends bearer and stored refresh for body logout', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    getAccessTokenMock.mockReturnValue('current-access')
    configureBodyRefreshTokenStore({
      read: vi.fn(async () => ({
        token: 'current-refresh',
        expiresAt: '2026-09-15T00:00:00Z',
      })),
      write: vi.fn(async () => undefined),
      clear: vi.fn(async () => undefined),
    })
    apiClientPostMock.mockResolvedValueOnce({
      response: { status: 204 },
      data: undefined,
      error: undefined,
    })

    await logout()

    expect(apiClientPostMock).toHaveBeenCalledWith('/api/v1/auth/logout/', {
      body: {
        refresh_token_transport: 'body',
        refresh_token: 'current-refresh',
      },
      credentials: 'omit',
      headers: { Authorization: 'Bearer current-access' },
    })
  })

  it('does not tear down native push when account deletion fails', async () => {
    getAccessTokenMock.mockReturnValue('current-access')
    apiClientPostMock.mockResolvedValueOnce({
      response: { status: 409 },
      data: undefined,
      error: { code: 'organization_closure_required', detail: 'closure required' },
    })

    await expect(
      deleteAccount({ password: 'secret', close_organizations: false }),
    ).rejects.toMatchObject({ status: 409, code: 'organization_closure_required' })

    expect(runNativePushBeforeLogoutMock).not.toHaveBeenCalled()
    expect(clearPendingNativeDeepLinkMock).not.toHaveBeenCalled()
  })

  it('tears down native push only after a successful account deletion', async () => {
    getAccessTokenMock.mockReturnValue('current-access')
    apiClientPostMock.mockResolvedValueOnce({
      response: { status: 204 },
      data: undefined,
      error: undefined,
    })

    await deleteAccount({ password: 'secret', close_organizations: false })

    expect(apiClientPostMock).toHaveBeenCalledWith(
      '/api/v1/auth/me/delete/',
      expect.objectContaining({
        body: expect.objectContaining({
          password: 'secret',
          close_organizations: false,
        }),
      }),
    )
    expect(runNativePushBeforeLogoutMock).toHaveBeenCalledOnce()
    expect(clearPendingNativeDeepLinkMock).toHaveBeenCalledOnce()
    expect(apiClientPostMock.mock.invocationCallOrder[0]).toBeLessThan(
      runNativePushBeforeLogoutMock.mock.invocationCallOrder[0],
    )
    expect(runNativePushBeforeLogoutMock.mock.invocationCallOrder[0]).toBeLessThan(
      clearPendingNativeDeepLinkMock.mock.invocationCallOrder[0],
    )
  })

  it('still tears down native push before logout', async () => {
    getAccessTokenMock.mockReturnValue('current-access')
    apiClientPostMock.mockResolvedValueOnce({
      response: { status: 204 },
      data: undefined,
      error: undefined,
    })

    await logout()

    expect(runNativePushBeforeLogoutMock).toHaveBeenCalledOnce()
    expect(runNativePushBeforeLogoutMock.mock.invocationCallOrder[0]).toBeLessThan(
      apiClientPostMock.mock.invocationCallOrder[0],
    )
  })

  it('still logs out with bearer when body refresh storage is unavailable', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    getAccessTokenMock.mockReturnValue('current-access')
    configureBodyRefreshTokenStore({
      read: vi.fn(async () => {
        throw new Error('secure store unavailable')
      }),
      write: vi.fn(async () => undefined),
      clear: vi.fn(async () => undefined),
    })
    apiClientPostMock.mockResolvedValueOnce({
      response: { status: 204 },
      data: undefined,
      error: undefined,
    })

    await logout()

    expect(apiClientPostMock).toHaveBeenCalledWith('/api/v1/auth/logout/', {
      body: {
        refresh_token_transport: 'body',
      },
      credentials: 'omit',
      headers: { Authorization: 'Bearer current-access' },
    })
  })

  it('uses explicit body refresh fallback for logout without bearer', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    getAccessTokenMock.mockReturnValue(null)
    configureBodyRefreshTokenStore({
      read: vi.fn(async () => ({
        token: 'current-refresh',
        expiresAt: '2026-09-15T00:00:00Z',
      })),
      write: vi.fn(async () => undefined),
      clear: vi.fn(async () => undefined),
    })
    apiClientPostMock.mockResolvedValueOnce({
      response: { status: 204 },
      data: undefined,
      error: undefined,
    })

    await logout()

    expect(apiClientPostMock).toHaveBeenCalledWith('/api/v1/auth/logout/', {
      body: {
        refresh_token_transport: 'body',
        refresh_token: 'current-refresh',
      },
      credentials: 'omit',
      headers: undefined,
    })
  })

  it('keeps the newest body replacement when an older response arrives late', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    let persistedRefresh: string | null = null
    configureBodyRefreshTokenStore({
      read: vi.fn(async () =>
        persistedRefresh
          ? { token: persistedRefresh, expiresAt: '2026-09-15T00:00:00Z' }
          : null,
      ),
      write: vi.fn(async (value) => {
        persistedRefresh = value.token
      }),
      clear: vi.fn(async () => {
        persistedRefresh = null
      }),
    })
    const firstResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload & {
        refresh_token: string
        refresh_token_expires_at: string
      }
      error: undefined
    }>()
    const secondResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload & {
        refresh_token: string
        refresh_token_expires_at: string
      }
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => firstResponse.promise)
      .mockImplementationOnce(() => secondResponse.promise)
      .mockResolvedValueOnce({
        response: { status: 204 },
        data: undefined,
        error: undefined,
      })

    const firstLogin = login({ email: 'first@example.com', password: 'secret' })
    const secondLogin = login({ email: 'second@example.com', password: 'secret' })
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(2)
    })

    secondResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'second-access',
        user: { ...bootstrapPayload.user, id: 'second-user' },
        refresh_token: 'second-refresh',
        refresh_token_expires_at: '2026-09-15T00:00:00Z',
      },
      error: undefined,
    })
    const secondResult = await secondLogin
    expect(secondResult).toMatchObject({
      user: { id: 'second-user' },
    })
    expect(secondResult).not.toHaveProperty('refresh_token')
    expect(secondResult).not.toHaveProperty('access_token')

    firstResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'first-access',
        user: { ...bootstrapPayload.user, id: 'first-user' },
        refresh_token: 'first-refresh',
        refresh_token_expires_at: '2026-09-15T00:00:00Z',
      },
      error: undefined,
    })
    await expect(firstLogin).rejects.toThrow(/no longer current/)

    expect(persistedRefresh).toBe('second-refresh')
    expect(setAccessTokenMock).toHaveBeenCalledTimes(1)
    expect(setAccessTokenMock).toHaveBeenCalledWith('second-access')
    expect(queryClient.getQueryData(bootstrapQueryKey)).toMatchObject({
      user: { id: 'second-user' },
    })
    expect(apiClientPostMock).toHaveBeenNthCalledWith(
      3,
      '/api/v1/auth/logout/',
      expect.objectContaining({
        body: {
          refresh_token_transport: 'body',
          refresh_token: 'first-refresh',
        },
        credentials: 'omit',
      }),
    )
  })

  it('keeps a replacement session when an older body refresh arrives late', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    let persistedRefresh: string | null = 'old-refresh'
    configureBodyRefreshTokenStore({
      read: vi.fn(async () =>
        persistedRefresh
          ? { token: persistedRefresh, expiresAt: '2026-09-15T00:00:00Z' }
          : null,
      ),
      write: vi.fn(async (value) => {
        persistedRefresh = value.token
      }),
      clear: vi.fn(async () => {
        persistedRefresh = null
      }),
    })
    const refreshResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload & {
        refresh_token: string
        refresh_token_expires_at: string
      }
      error: undefined
    }>()
    const replacementResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload & {
        refresh_token: string
        refresh_token_expires_at: string
      }
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => refreshResponse.promise)
      .mockImplementationOnce(() => replacementResponse.promise)
      .mockResolvedValueOnce({
        response: { status: 204 },
        data: undefined,
        error: undefined,
      })

    const refreshPromise = refreshAccessToken()
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(1)
    })
    const replacementLogin = login({ email: 'replacement@example.com', password: 'secret' })
    replacementResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'replacement-access',
        user: { ...bootstrapPayload.user, id: 'replacement-user' },
        refresh_token: 'replacement-refresh',
        refresh_token_expires_at: '2026-09-15T00:00:00Z',
      },
      error: undefined,
    })
    await replacementLogin

    refreshResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'rotated-old-access',
        user: { ...bootstrapPayload.user, id: 'old-user' },
        refresh_token: 'rotated-old-refresh',
        refresh_token_expires_at: '2026-09-15T00:00:00Z',
      },
      error: undefined,
    })

    await expect(refreshPromise).resolves.toBeNull()
    expect(persistedRefresh).toBe('replacement-refresh')
    expect(clearAccessTokenMock).not.toHaveBeenCalled()
    expect(setAccessTokenMock).toHaveBeenCalledTimes(1)
    expect(setAccessTokenMock).toHaveBeenCalledWith('replacement-access')
    expect(queryClient.getQueryData(bootstrapQueryKey)).toMatchObject({
      user: { id: 'replacement-user' },
    })
  })

  it('keeps a body replacement when an older refresh fails after login starts', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    let persistedRefresh: string | null = 'old-refresh'
    configureBodyRefreshTokenStore({
      read: vi.fn(async () =>
        persistedRefresh
          ? { token: persistedRefresh, expiresAt: '2026-09-15T00:00:00Z' }
          : null,
      ),
      write: vi.fn(async (value) => {
        persistedRefresh = value.token
      }),
      clear: vi.fn(async () => {
        persistedRefresh = null
      }),
    })
    const refreshResponse = deferred<{
      response: { status: number }
      data: undefined
      error: { detail: string }
    }>()
    const loginResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload & {
        refresh_token: string
        refresh_token_expires_at: string
      }
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => refreshResponse.promise)
      .mockImplementationOnce(() => loginResponse.promise)

    const refreshPromise = refreshAccessToken()
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(1)
    })
    const loginPromise = login({ email: 'replacement@example.com', password: 'secret' })
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(2)
    })

    loginResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'replacement-access',
        user: { ...bootstrapPayload.user, id: 'replacement-user' },
        refresh_token: 'replacement-refresh',
        refresh_token_expires_at: '2026-09-15T00:00:00Z',
      },
      error: undefined,
    })
    await loginPromise
    expect(persistedRefresh).toBe('replacement-refresh')

    refreshResponse.resolve({
      response: { status: 401 },
      data: undefined,
      error: { detail: 'Your session could not be refreshed.' },
    })
    await expect(refreshPromise).resolves.toBeNull()

    expect(persistedRefresh).toBe('replacement-refresh')
    expect(clearAccessTokenMock).not.toHaveBeenCalled()
    expect(setAccessTokenMock).toHaveBeenCalledTimes(1)
    expect(setAccessTokenMock).toHaveBeenCalledWith('replacement-access')
    expect(queryClient.getQueryData(bootstrapQueryKey)).toMatchObject({
      user: { id: 'replacement-user' },
    })
  })

  it('waits for an in-flight body login before refreshing the new session', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    let persistedRefresh: string | null = 'old-refresh'
    configureBodyRefreshTokenStore({
      read: vi.fn(async () =>
        persistedRefresh
          ? { token: persistedRefresh, expiresAt: '2026-09-15T00:00:00Z' }
          : null,
      ),
      write: vi.fn(async (value) => {
        persistedRefresh = value.token
      }),
      clear: vi.fn(async () => {
        persistedRefresh = null
      }),
    })
    const loginResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload & {
        refresh_token: string
        refresh_token_expires_at: string
      }
      error: undefined
    }>()
    const refreshResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload & {
        refresh_token: string
        refresh_token_expires_at: string
      }
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => loginResponse.promise)
      .mockImplementationOnce(() => refreshResponse.promise)

    const loginPromise = login({ email: 'replacement@example.com', password: 'secret' })
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(1)
    })
    const refreshPromise = refreshAccessToken()
    await Promise.resolve()
    expect(apiClientPostMock).toHaveBeenCalledTimes(1)

    loginResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'replacement-access',
        user: { ...bootstrapPayload.user, id: 'replacement-user' },
        refresh_token: 'replacement-refresh',
        refresh_token_expires_at: '2026-09-15T00:00:00Z',
      },
      error: undefined,
    })
    await loginPromise
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(2)
    })
    expect(apiClientPostMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/auth/refresh/',
      expect.objectContaining({
        body: {
          refresh_token_transport: 'body',
          refresh_token: 'replacement-refresh',
        },
      }),
    )

    refreshResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'rotated-replacement-access',
        user: { ...bootstrapPayload.user, id: 'replacement-user' },
        refresh_token: 'rotated-replacement-refresh',
        refresh_token_expires_at: '2026-09-15T00:00:00Z',
      },
      error: undefined,
    })

    await expect(refreshPromise).resolves.toBe('rotated-replacement-access')
    expect(persistedRefresh).toBe('rotated-replacement-refresh')
    expect(clearAccessTokenMock).not.toHaveBeenCalled()
    expect(setAccessTokenMock).toHaveBeenCalledWith('replacement-access')
    expect(setAccessTokenMock).toHaveBeenCalledWith('rotated-replacement-access')
    expect(queryClient.getQueryData(bootstrapQueryKey)).toMatchObject({
      user: { id: 'replacement-user' },
    })
  })

  it('refreshes the existing body session after a failed concurrent login', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    let persistedRefresh: string | null = 'old-refresh'
    configureBodyRefreshTokenStore({
      read: vi.fn(async () =>
        persistedRefresh
          ? { token: persistedRefresh, expiresAt: '2026-09-15T00:00:00Z' }
          : null,
      ),
      write: vi.fn(async (value) => {
        persistedRefresh = value.token
      }),
      clear: vi.fn(async () => {
        persistedRefresh = null
      }),
    })
    const loginResponse = deferred<{
      response: { status: number }
      data: undefined
      error: { detail: string }
    }>()
    const refreshResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload & {
        refresh_token: string
        refresh_token_expires_at: string
      }
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => loginResponse.promise)
      .mockImplementationOnce(() => refreshResponse.promise)

    const loginPromise = login({ email: 'other@example.com', password: 'wrong' })
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(1)
    })
    const refreshPromise = refreshAccessToken()
    await Promise.resolve()
    expect(apiClientPostMock).toHaveBeenCalledTimes(1)

    loginResponse.resolve({
      response: { status: 401 },
      data: undefined,
      error: { detail: 'Sign-in failed.' },
    })
    await expect(loginPromise).rejects.toThrow(/Sign-in failed/)
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(2)
    })
    expect(apiClientPostMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/auth/refresh/',
      expect.objectContaining({
        body: {
          refresh_token_transport: 'body',
          refresh_token: 'old-refresh',
        },
      }),
    )

    refreshResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'rotated-old-access',
        user: { ...bootstrapPayload.user, id: 'old-user' },
        refresh_token: 'rotated-old-refresh',
        refresh_token_expires_at: '2026-09-15T00:00:00Z',
      },
      error: undefined,
    })

    await expect(refreshPromise).resolves.toBe('rotated-old-access')
    expect(persistedRefresh).toBe('rotated-old-refresh')
    expect(clearAccessTokenMock).not.toHaveBeenCalled()
    expect(setAccessTokenMock).toHaveBeenCalledTimes(1)
    expect(setAccessTokenMock).toHaveBeenCalledWith('rotated-old-access')
    expect(queryClient.getQueryData(bootstrapQueryKey)).toMatchObject({
      user: { id: 'old-user' },
    })
  })

  const bodyReplacementCases = [
    {
      name: 'login',
      start: () => login({ email: 'other@example.com', password: 'wrong' }),
      failure: {
        status: 401,
        detail: 'Sign-in failed.',
        pattern: /Sign-in failed/,
      },
    },
    {
      name: 'invitation',
      start: () =>
        acceptInvitationSession('invite-token', {
          password: 'secret',
          password_confirmation: 'secret',
        }),
      failure: {
        status: 400,
        detail: 'Invitation could not be accepted.',
        pattern: /Invitation could not be accepted/,
      },
    },
  ] as const

  function configureBodyRefreshStore(initialToken: string | null = 'old-refresh') {
    let persistedRefresh: string | null = initialToken
    configureBodyRefreshTokenStore({
      read: vi.fn(async () =>
        persistedRefresh
          ? { token: persistedRefresh, expiresAt: '2026-09-15T00:00:00Z' }
          : null,
      ),
      write: vi.fn(async (value) => {
        persistedRefresh = value.token
      }),
      clear: vi.fn(async () => {
        persistedRefresh = null
      }),
    })
    return {
      get persistedRefresh() {
        return persistedRefresh
      },
    }
  }

  for (const replacement of bodyReplacementCases) {
    it(`installs a rotated body session when an in-flight refresh succeeds after a failed ${replacement.name}`, async () => {
      vi.stubEnv('VITE_APP_RUNTIME', 'native')
      const store = configureBodyRefreshStore()
      const refreshResponse = deferred<{
        response: { status: number }
        data: typeof bootstrapPayload & {
          refresh_token: string
          refresh_token_expires_at: string
        }
        error: undefined
      }>()
      const replacementResponse = deferred<{
        response: { status: number }
        data: undefined
        error: { detail: string }
      }>()
      apiClientPostMock
        .mockImplementationOnce(() => refreshResponse.promise)
        .mockImplementationOnce(() => replacementResponse.promise)

      const refreshPromise = refreshAccessToken()
      await vi.waitFor(() => {
        expect(apiClientPostMock).toHaveBeenCalledTimes(1)
      })
      const replacementPromise = replacement.start()
      await vi.waitFor(() => {
        expect(apiClientPostMock).toHaveBeenCalledTimes(2)
      })

      replacementResponse.resolve({
        response: { status: replacement.failure.status },
        data: undefined,
        error: { detail: replacement.failure.detail },
      })
      await expect(replacementPromise).rejects.toThrow(replacement.failure.pattern)

      refreshResponse.resolve({
        response: { status: 200 },
        data: {
          ...bootstrapPayload,
          access_token: 'rotated-old-access',
          user: { ...bootstrapPayload.user, id: 'old-user' },
          refresh_token: 'rotated-old-refresh',
          refresh_token_expires_at: '2026-09-15T00:00:00Z',
        },
        error: undefined,
      })

      await expect(refreshPromise).resolves.toBe('rotated-old-access')
      expect(store.persistedRefresh).toBe('rotated-old-refresh')
      expect(clearAccessTokenMock).not.toHaveBeenCalled()
      expect(setAccessTokenMock).toHaveBeenCalledTimes(1)
      expect(setAccessTokenMock).toHaveBeenCalledWith('rotated-old-access')
      expect(queryClient.getQueryData(bootstrapQueryKey)).toMatchObject({
        user: { id: 'old-user' },
      })
      expect(apiClientPostMock).toHaveBeenCalledTimes(2)
    })

    it(`clears the body session when an in-flight refresh fails after a failed ${replacement.name}`, async () => {
      vi.stubEnv('VITE_APP_RUNTIME', 'native')
      const store = configureBodyRefreshStore()
      const refreshResponse = deferred<{
        response: { status: number }
        data: undefined
        error: { detail: string }
      }>()
      const replacementResponse = deferred<{
        response: { status: number }
        data: undefined
        error: { detail: string }
      }>()
      apiClientPostMock
        .mockImplementationOnce(() => refreshResponse.promise)
        .mockImplementationOnce(() => replacementResponse.promise)

      const refreshPromise = refreshAccessToken()
      await vi.waitFor(() => {
        expect(apiClientPostMock).toHaveBeenCalledTimes(1)
      })
      const replacementPromise = replacement.start()
      await vi.waitFor(() => {
        expect(apiClientPostMock).toHaveBeenCalledTimes(2)
      })

      replacementResponse.resolve({
        response: { status: replacement.failure.status },
        data: undefined,
        error: { detail: replacement.failure.detail },
      })
      await expect(replacementPromise).rejects.toThrow(replacement.failure.pattern)

      refreshResponse.resolve({
        response: { status: 401 },
        data: undefined,
        error: { detail: 'Your session could not be refreshed.' },
      })

      await expect(refreshPromise).resolves.toBeNull()
      expect(store.persistedRefresh).toBeNull()
      expect(clearAccessTokenMock).toHaveBeenCalled()
      expect(setAccessTokenMock).not.toHaveBeenCalled()
    })
  }

  it('waits for an in-flight cookie login before refreshing the new session', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    const loginResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload
      error: undefined
    }>()
    const refreshResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => loginResponse.promise)
      .mockImplementationOnce(() => refreshResponse.promise)

    const loginPromise = login({ email: 'replacement@example.com', password: 'secret' })
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(1)
    })
    const refreshPromise = refreshAccessToken()
    await Promise.resolve()
    expect(apiClientPostMock).toHaveBeenCalledTimes(1)

    loginResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'replacement-access',
        user: { ...bootstrapPayload.user, id: 'replacement-user' },
      },
      error: undefined,
    })
    await loginPromise
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(2)
    })
    expect(apiClientPostMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/auth/refresh/',
      expect.objectContaining({
        body: { refresh_token_transport: 'cookie' },
      }),
    )

    refreshResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'rotated-replacement-access',
        user: { ...bootstrapPayload.user, id: 'replacement-user' },
      },
      error: undefined,
    })

    await expect(refreshPromise).resolves.toBe('rotated-replacement-access')
    expect(clearAccessTokenMock).not.toHaveBeenCalled()
    expect(setAccessTokenMock).toHaveBeenCalledWith('replacement-access')
    expect(setAccessTokenMock).toHaveBeenCalledWith('rotated-replacement-access')
    expect(queryClient.getQueryData(bootstrapQueryKey)).toMatchObject({
      user: { id: 'replacement-user' },
    })
  })

  it('does not let a cookie refresh overlap a later login request', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    const refreshResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload
      error: undefined
    }>()
    const loginResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => refreshResponse.promise)
      .mockImplementationOnce(() => loginResponse.promise)

    const refreshPromise = refreshAccessToken()
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(1)
    })
    expect(apiClientPostMock).toHaveBeenNthCalledWith(1, '/api/v1/auth/refresh/', expect.anything())

    const loginPromise = login({ email: 'replacement@example.com', password: 'secret' })
    await Promise.resolve()
    expect(apiClientPostMock).toHaveBeenCalledTimes(1)

    refreshResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'rotated-old-access',
        user: { ...bootstrapPayload.user, id: 'old-user' },
      },
      error: undefined,
    })
    await expect(refreshPromise).resolves.toBe('rotated-old-access')
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(2)
    })
    expect(apiClientPostMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/auth/login/',
      expect.objectContaining({
        body: expect.objectContaining({ refresh_token_transport: 'cookie' }),
      }),
    )

    loginResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'replacement-access',
        user: { ...bootstrapPayload.user, id: 'replacement-user' },
      },
      error: undefined,
    })
    await loginPromise

    expect(setAccessTokenMock).toHaveBeenCalledWith('rotated-old-access')
    expect(setAccessTokenMock).toHaveBeenLastCalledWith('replacement-access')
    expect(queryClient.getQueryData(bootstrapQueryKey)).toMatchObject({
      user: { id: 'replacement-user' },
    })
    expect(apiClientPostMock).not.toHaveBeenCalledWith(
      '/api/v1/auth/logout/',
      expect.anything(),
    )
  })

  it('keeps a cookie login queued behind a refresh that then fails', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    const refreshResponse = deferred<{
      response: { status: number }
      data: undefined
      error: { detail: string }
    }>()
    const loginResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => refreshResponse.promise)
      .mockImplementationOnce(() => loginResponse.promise)

    const refreshPromise = refreshAccessToken()
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(1)
    })
    const loginPromise = login({ email: 'replacement@example.com', password: 'secret' })
    await Promise.resolve()
    expect(apiClientPostMock).toHaveBeenCalledTimes(1)

    refreshResponse.resolve({
      response: { status: 401 },
      data: undefined,
      error: { detail: 'Your session could not be refreshed.' },
    })
    await expect(refreshPromise).resolves.toBeNull()
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(2)
    })

    loginResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'replacement-access',
        user: { ...bootstrapPayload.user, id: 'replacement-user' },
      },
      error: undefined,
    })
    await expect(loginPromise).resolves.toMatchObject({
      user: { id: 'replacement-user' },
    })
    expect(setAccessTokenMock).toHaveBeenCalledWith('replacement-access')
    expect(queryClient.getQueryData(bootstrapQueryKey)).toMatchObject({
      user: { id: 'replacement-user' },
    })
  })

  it('serializes cookie replacements before sending their requests', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    const firstResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload
      error: undefined
    }>()
    const secondResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => firstResponse.promise)
      .mockImplementationOnce(() => secondResponse.promise)

    const firstLogin = login({ email: 'first@example.com', password: 'secret' })
    const secondLogin = login({ email: 'second@example.com', password: 'secret' })
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(1)
    })

    firstResponse.resolve({
      response: { status: 200 },
      data: { ...bootstrapPayload, access_token: 'first-access' },
      error: undefined,
    })
    await firstLogin
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(2)
    })

    secondResponse.resolve({
      response: { status: 200 },
      data: { ...bootstrapPayload, access_token: 'second-access' },
      error: undefined,
    })
    await secondLogin

    expect(setAccessTokenMock).toHaveBeenNthCalledWith(1, 'first-access')
    expect(setAccessTokenMock).toHaveBeenNthCalledWith(2, 'second-access')
  })

  it('fails closed and cancels queued cookie replacement after logout invalidation', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    const firstResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => firstResponse.promise)
      .mockResolvedValueOnce({
        response: { status: 204 },
        data: undefined,
        error: undefined,
      })
      .mockResolvedValueOnce({
        response: { status: 204 },
        data: undefined,
        error: undefined,
      })

    const firstLogin = login({ email: 'first@example.com', password: 'secret' })
    const queuedLogin = login({ email: 'queued@example.com', password: 'secret' })
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(1)
    })
    await logout()
    clearAuthState()

    firstResponse.resolve({
      response: { status: 200 },
      data: { ...bootstrapPayload, access_token: 'stale-cookie-access' },
      error: undefined,
    })

    await expect(firstLogin).rejects.toThrow(/no longer current/)
    await expect(queuedLogin).rejects.toThrow(/no longer current/)
    expect(setAccessTokenMock).not.toHaveBeenCalled()
    expect(queryClient.getQueryData(bootstrapQueryKey)).toBeUndefined()
    expect(apiClientPostMock).toHaveBeenCalledTimes(3)
    expect(apiClientPostMock).toHaveBeenNthCalledWith(3, '/api/v1/auth/logout/', {
      body: { refresh_token_transport: 'cookie' },
      credentials: 'include',
      headers: {
        Authorization: 'Bearer stale-cookie-access',
        'X-CSRFToken': 'csrf-token',
      },
    })
  })

  it('keeps a cookie login started after logout when a stale login is still in flight', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    const staleResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload
      error: undefined
    }>()
    const nextResponse = deferred<{
      response: { status: number }
      data: typeof bootstrapPayload
      error: undefined
    }>()
    apiClientPostMock
      .mockImplementationOnce(() => staleResponse.promise)
      .mockResolvedValueOnce({
        response: { status: 204 },
        data: undefined,
        error: undefined,
      })
      .mockResolvedValueOnce({
        response: { status: 204 },
        data: undefined,
        error: undefined,
      })
      .mockImplementationOnce(() => nextResponse.promise)

    const staleLogin = login({ email: 'stale@example.com', password: 'secret' })
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(1)
    })
    await logout()
    clearAuthState()
    const nextLogin = login({ email: 'next@example.com', password: 'secret' })

    staleResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'stale-cookie-access',
        user: { ...bootstrapPayload.user, id: 'stale-user' },
      },
      error: undefined,
    })
    await expect(staleLogin).rejects.toThrow(/no longer current/)
    await vi.waitFor(() => {
      expect(apiClientPostMock).toHaveBeenCalledTimes(4)
    })

    nextResponse.resolve({
      response: { status: 200 },
      data: {
        ...bootstrapPayload,
        access_token: 'next-cookie-access',
        user: { ...bootstrapPayload.user, id: 'next-user' },
      },
      error: undefined,
    })
    await expect(nextLogin).resolves.toMatchObject({
      user: { id: 'next-user' },
    })
    expect(setAccessTokenMock).toHaveBeenCalledTimes(1)
    expect(setAccessTokenMock).toHaveBeenCalledWith('next-cookie-access')
    expect(queryClient.getQueryData(bootstrapQueryKey)).toMatchObject({
      user: { id: 'next-user' },
    })
  })

  describe('confirmPasswordReset', () => {
    it('uses password field errors as the AuthApiError message', async () => {
      apiClientPostMock.mockResolvedValueOnce({
        response: { status: 400 },
        data: undefined,
        error: { password: ['This password is too common.'] },
      })

      await expect(
        confirmPasswordReset({
          token: 'reset-token',
          password: 'weak',
          password_confirmation: 'weak',
        }),
      ).rejects.toMatchObject({
        name: 'AuthApiError',
        message: 'This password is too common.',
        code: null,
      })
    })
  })

})
