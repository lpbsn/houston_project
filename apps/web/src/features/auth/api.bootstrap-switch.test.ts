import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  __resetObservationComposeDraftStoreForTests,
  getReportingComposeDraft,
  setReportingComposeText,
} from '@/features/observations/lib/observation-compose-draft-store'
import { queryClient } from '@/lib/query-client'
import {
  getSuccessToastsSnapshot,
  notifySuccess,
  resetSuccessToastsForTests,
} from '@/lib/success-toast'
import {
  clearAuthState,
  fetchBootstrap,
  login,
  refreshAccessToken,
  switchEstablishment,
} from '@/features/auth/api'
import { clearBodyRefreshTokenStoreConfiguration } from './refresh-token-transport'
import {
  bootstrapPayload,
  bootstrapQueryKey,
  expectStaleNonAuthQueriesPurged,
  seedStaleNonAuthQueries,
} from './api.test-setup'

const {
  withAuthRetryMock,
  apiClientGetMock,
  apiClientPostMock,
  clearAccessTokenMock,
  setAccessTokenMock,
  getAccessTokenMock,
} = vi.hoisted(() => ({
  withAuthRetryMock: vi.fn(),
  apiClientGetMock: vi.fn(),
  apiClientPostMock: vi.fn(),
  clearAccessTokenMock: vi.fn(),
  setAccessTokenMock: vi.fn(),
  getAccessTokenMock: vi.fn(),
}))

const clearCsrfTokenCacheMock = vi.hoisted(() => vi.fn())

vi.mock('@/api/client', () => ({
  apiClient: {
    GET: (...args: unknown[]) => apiClientGetMock(...args),
    POST: (...args: unknown[]) => apiClientPostMock(...args),
  },
  withAuthRetry: (...args: unknown[]) => withAuthRetryMock(...args),
}))

vi.mock('./csrf', () => ({
  clearCsrfTokenCache: () => clearCsrfTokenCacheMock(),
  ensureCsrfToken: vi.fn(async () => 'csrf-token'),
}))

vi.mock('./session', () => ({
  clearAccessToken: () => clearAccessTokenMock(),
  getAccessToken: () => getAccessTokenMock(),
  setAccessToken: (token: string) => setAccessTokenMock(token),
}))

vi.mock('@/lib/native-push-session', () => ({
  runNativePushBeforeLogout: vi.fn(async () => undefined),
}))

vi.mock('@/lib/native-deep-link-session', () => ({
  clearPendingNativeDeepLink: vi.fn(),
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

describe('auth api bootstrap switch', () => {
  beforeEach(() => {
    resetAuthApiTest()
  })

  afterEach(() => {
    cleanupAuthApiTest()
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

  describe('observation compose draft purge', () => {
    const composeText = 'Tache visible sur le mur.'

    function seedComposeDraft() {
      setReportingComposeText('est-a', composeText)
    }

    function expectComposeDraftKept() {
      expect(getReportingComposeDraft('est-a').text).toBe(composeText)
    }

    function expectComposeDraftCleared() {
      expect(getReportingComposeDraft('est-a').text).toBe('')
    }

    it.each([
      {
        name: 'network failure',
        mockRefresh: () => {
          apiClientPostMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
        },
      },
      {
        name: '401',
        mockRefresh: () => {
          apiClientPostMock.mockResolvedValueOnce({
            response: { status: 401 },
            data: undefined,
            error: { detail: 'Your session could not be refreshed.' },
          })
        },
      },
    ])('keeps the compose draft when refresh fails ($name)', async ({ mockRefresh }) => {
      vi.stubEnv('VITE_APP_RUNTIME', 'web')
      seedComposeDraft()
      mockRefresh()

      await expect(refreshAccessToken()).resolves.toBeNull()

      expect(clearAccessTokenMock).toHaveBeenCalled()
      expectComposeDraftKept()
    })

    it('clears the compose draft on clearAuthState', () => {
      seedComposeDraft()

      clearAuthState()

      expectComposeDraftCleared()
    })

    it('clears the compose draft on login', async () => {
      seedComposeDraft()
      apiClientPostMock.mockResolvedValueOnce({
        response: { status: 200 },
        data: bootstrapPayload,
        error: undefined,
      })

      await login({ email: 'owner@example.com', password: 'secret' })

      expectComposeDraftCleared()
    })

    it('clears the compose draft when switching establishment', async () => {
      seedComposeDraft()
      withAuthRetryMock.mockResolvedValueOnce({
        response: { status: 200 },
        data: bootstrapPayload,
        error: undefined,
      })

      await switchEstablishment({ establishment_id: 'est-b' })

      expectComposeDraftCleared()
    })
  })

  describe('fetchBootstrap', () => {
    it('writes a successful bootstrap fetch into the query cache', async () => {
      const staleBootstrap = {
        ...bootstrapPayload,
        user: { ...bootstrapPayload.user, email: 'old@example.com' },
      }
      const nextBootstrap = {
        ...bootstrapPayload,
        user: { ...bootstrapPayload.user, email: 'next@example.com' },
      }
      queryClient.setQueryData(bootstrapQueryKey, staleBootstrap)
      withAuthRetryMock.mockResolvedValueOnce({
        response: { status: 200 },
        data: nextBootstrap,
        error: undefined,
      })

      const result = await fetchBootstrap()

      expect(result).toEqual(nextBootstrap)
      expect(queryClient.getQueryData(bootstrapQueryKey)).toEqual(nextBootstrap)
    })
  })

})
