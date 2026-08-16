import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { queryClient } from '@/lib/query-client'
import {
  getSuccessToastsSnapshot,
  notifySuccess,
  resetSuccessToastsForTests,
} from '@/lib/success-toast'
import {
  clearBodyRefreshTokenStoreConfiguration,
  configureBodyRefreshTokenStore,
} from './refresh-token-transport'

const {
  withAuthRetryMock,
  apiClientPostMock,
  clearAccessTokenMock,
  setAccessTokenMock,
  getAccessTokenMock,
} = vi.hoisted(() => ({
  withAuthRetryMock: vi.fn(),
  apiClientPostMock: vi.fn(),
  clearAccessTokenMock: vi.fn(),
  setAccessTokenMock: vi.fn(),
  getAccessTokenMock: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  apiClient: {
    POST: (...args: unknown[]) => apiClientPostMock(...args),
  },
  withAuthRetry: (...args: unknown[]) => withAuthRetryMock(...args),
}))

const clearCsrfTokenCacheMock = vi.hoisted(() => vi.fn())

vi.mock('./csrf', () => ({
  clearCsrfTokenCache: () => clearCsrfTokenCacheMock(),
  ensureCsrfToken: vi.fn(async () => 'csrf-token'),
}))

vi.mock('./session', () => ({
  clearAccessToken: () => clearAccessTokenMock(),
  getAccessToken: () => getAccessTokenMock(),
  setAccessToken: (token: string) => setAccessTokenMock(token),
}))

import {
  bootstrapQueryKey,
  clearAuthState,
  login,
  logout,
  refreshAccessToken,
  registerOnboarding,
  switchEstablishment,
} from '@/features/auth/api'

const bootstrapPayload = {
  authenticated: true,
  access_token: 'new-access-token',
  user: { id: 'u1', username: 'owner', email: 'owner@example.com' },
  memberships: [],
  active_membership: {
    id: 'm2',
    establishment_id: 'est-b',
    establishment_name: 'Establishment B',
    role: 'manager',
    status: 'active',
  },
  pending_onboarding_memberships: [],
  permission_hints: {},
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, reject, resolve }
}

function seedStaleNonAuthQueries() {
  queryClient.setQueryData(['signals', 'feed', 'est-a', 'general', {}], { items: ['stale'] })
  queryClient.setQueryData(['workspace', 'summary', 'est-a'], { name: 'A' })
  queryClient.setQueryData(['reporting', 'kpi', 'est-a'], { kpi: 1 })
  queryClient.setQueryData(['onboarding', 'sessions', 's-1'], { id: 's-1' })
  queryClient.setQueryData(['chat', 'status', 'est-a'], { chat_enabled: true, can_access: true })
  queryClient.setQueryData(['chat', 'conversations', 'est-a'], { items: [] })
  queryClient.setQueryData(bootstrapQueryKey, {
    ...bootstrapPayload,
    active_membership: {
      ...bootstrapPayload.active_membership,
      establishment_id: 'est-a',
    },
  })
}

function expectStaleNonAuthQueriesPurged() {
  expect(queryClient.getQueryData(['signals', 'feed', 'est-a', 'general', {}])).toBeUndefined()
  expect(queryClient.getQueryData(['workspace', 'summary', 'est-a'])).toBeUndefined()
  expect(queryClient.getQueryData(['reporting', 'kpi', 'est-a'])).toBeUndefined()
  expect(queryClient.getQueryData(['onboarding', 'sessions', 's-1'])).toBeUndefined()
  expect(queryClient.getQueryData(['chat', 'status', 'est-a'])).toBeUndefined()
  expect(queryClient.getQueryData(['chat', 'conversations', 'est-a'])).toBeUndefined()
}

describe('auth api cache isolation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    queryClient.clear()
    resetSuccessToastsForTests()
    withAuthRetryMock.mockImplementation(async (execute: (token: string | null) => Promise<unknown>) =>
      execute('access-token'),
    )
  })

  afterEach(() => {
    clearBodyRefreshTokenStoreConfiguration()
    vi.unstubAllEnvs()
  })

  it('purges non-auth queries when switching establishment', async () => {
    seedStaleNonAuthQueries()
    notifySuccess({ message: 'stale toast', kind: 'created' })

    withAuthRetryMock.mockResolvedValueOnce({
      response: { status: 200 },
      data: bootstrapPayload,
      error: undefined,
    })

    const result = await switchEstablishment({ establishment_id: 'est-b' })

    expect(result).toEqual(bootstrapPayload)
    expectStaleNonAuthQueriesPurged()
    expect(queryClient.getQueryData(bootstrapQueryKey)).toEqual(bootstrapPayload)
    expect(getSuccessToastsSnapshot()).toEqual([])
  })

  it('purges non-auth queries on login', async () => {
    seedStaleNonAuthQueries()
    notifySuccess({ message: 'stale toast', kind: 'created' })

    apiClientPostMock.mockResolvedValueOnce({
      response: { status: 200 },
      data: bootstrapPayload,
      error: undefined,
    })

    const result = await login({ email: 'owner@example.com', password: 'secret' })

    expect(result).toEqual({
      authenticated: bootstrapPayload.authenticated,
      user: bootstrapPayload.user,
      memberships: bootstrapPayload.memberships,
      active_membership: bootstrapPayload.active_membership,
      pending_onboarding_memberships: bootstrapPayload.pending_onboarding_memberships,
      permission_hints: bootstrapPayload.permission_hints,
    })
    expectStaleNonAuthQueriesPurged()
    expect(queryClient.getQueryData(bootstrapQueryKey)).toEqual({
      authenticated: bootstrapPayload.authenticated,
      user: bootstrapPayload.user,
      memberships: bootstrapPayload.memberships,
      active_membership: bootstrapPayload.active_membership,
      pending_onboarding_memberships: bootstrapPayload.pending_onboarding_memberships,
      permission_hints: bootstrapPayload.permission_hints,
    })
    expect(setAccessTokenMock).toHaveBeenCalledWith('new-access-token')
    expect(getSuccessToastsSnapshot()).toEqual([])
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

  it('uses bearer without reading body refresh storage for logout', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    getAccessTokenMock.mockReturnValue('current-access')
    const store = {
      read: vi.fn(async () => {
        throw new Error('secure store unavailable')
      }),
      write: vi.fn(async () => undefined),
      clear: vi.fn(async () => undefined),
    }
    configureBodyRefreshTokenStore(store)
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
    expect(store.read).not.toHaveBeenCalled()
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

  it('purges non-auth queries on registerOnboarding', async () => {
    seedStaleNonAuthQueries()
    notifySuccess({ message: 'stale toast', kind: 'created' })

    apiClientPostMock.mockResolvedValueOnce({
      response: { status: 201 },
      data: {
        ...bootstrapPayload,
        establishment_id: 'est-new',
        onboarding_session_id: 'session-new',
      },
      error: undefined,
    })

    const result = await registerOnboarding({
      invite_code: 'INVITE',
      first_name: 'Owner',
      last_name: 'Example',
      email: 'owner@example.com',
      password: 'secret',
      password_confirmation: 'secret',
    })

    expect(result).toEqual({
      establishment_id: 'est-new',
      onboarding_session_id: 'session-new',
    })
    expectStaleNonAuthQueriesPurged()
    expect(queryClient.getQueryData(bootstrapQueryKey)).toEqual({
      authenticated: bootstrapPayload.authenticated,
      user: bootstrapPayload.user,
      memberships: bootstrapPayload.memberships,
      active_membership: bootstrapPayload.active_membership,
      pending_onboarding_memberships: bootstrapPayload.pending_onboarding_memberships,
      permission_hints: bootstrapPayload.permission_hints,
    })
    expect(setAccessTokenMock).toHaveBeenCalledWith('new-access-token')
    expect(getSuccessToastsSnapshot()).toEqual([])
  })

  it('clears cached frontend auth state on clearAuthState', () => {
    queryClient.setQueryData(['action-plans', 'detail', 'est-a', 'plan-1'], { id: 'plan-1' })
    queryClient.setQueryData(['chat', 'conversations', 'est-a'], { items: [] })
    queryClient.setQueryData(['reporting', 'kpi', 'est-a'], { kpi: 1 })
    queryClient.setQueryData(bootstrapQueryKey, bootstrapPayload)
    notifySuccess({ message: 'stale toast', kind: 'created' })

    clearAuthState()

    expect(clearCsrfTokenCacheMock).toHaveBeenCalledOnce()
    expect(clearAccessTokenMock).toHaveBeenCalledOnce()
    expect(queryClient.getQueryData(['action-plans', 'detail', 'est-a', 'plan-1'])).toBeUndefined()
    expect(queryClient.getQueryData(['chat', 'conversations', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['reporting', 'kpi', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(bootstrapQueryKey)).toBeUndefined()
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0)
    expect(getSuccessToastsSnapshot()).toEqual([])
  })
})
