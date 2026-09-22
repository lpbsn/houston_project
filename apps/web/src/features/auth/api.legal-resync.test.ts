import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AI_CONSENT_REQUIRED_CODE } from '@/lib/legal'
import { queryClient } from '@/lib/query-client'
import { resetSuccessToastsForTests } from '@/lib/success-toast'
import { __resetObservationComposeDraftStoreForTests } from '@/features/observations/lib/observation-compose-draft-store'
import { resyncBootstrapAfterLegalError } from '@/features/auth/api'
import { clearBodyRefreshTokenStoreConfiguration } from './refresh-token-transport'
import { bootstrapPayload, bootstrapQueryKey } from './api.test-setup'

const { withAuthRetryMock, apiClientGetMock, apiClientPostMock } = vi.hoisted(() => ({
  withAuthRetryMock: vi.fn(),
  apiClientGetMock: vi.fn(),
  apiClientPostMock: vi.fn(),
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
  clearAccessToken: vi.fn(),
  getAccessToken: vi.fn(),
  setAccessToken: vi.fn(),
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

describe('auth api legal resync', () => {
  beforeEach(() => {
    resetAuthApiTest()
  })

  afterEach(() => {
    cleanupAuthApiTest()
  })

  describe('resyncBootstrapAfterLegalError', () => {
    it('returns null without fetching bootstrap for a non-legal error', async () => {
      const result = await resyncBootstrapAfterLegalError({ code: 'permission_denied' })

      expect(result).toBeNull()
      expect(apiClientGetMock).not.toHaveBeenCalled()
    })

    it('writes a successful bootstrap fetch into the query cache', async () => {
      const staleBootstrap = {
        ...bootstrapPayload,
        user: { ...bootstrapPayload.user, ai_consent_status: 'granted' },
      }
      const nextBootstrap = {
        ...bootstrapPayload,
        user: { ...bootstrapPayload.user, ai_consent_status: 'declined' },
      }
      queryClient.setQueryData(bootstrapQueryKey, staleBootstrap)
      apiClientGetMock.mockResolvedValueOnce({
        response: { status: 200 },
        data: nextBootstrap,
        error: undefined,
      })

      const result = await resyncBootstrapAfterLegalError({ code: AI_CONSENT_REQUIRED_CODE })

      expect(result).toEqual(nextBootstrap)
      expect(queryClient.getQueryData(bootstrapQueryKey)).toEqual(nextBootstrap)
    })

    it('returns null without throwing when bootstrap fetch fails', async () => {
      queryClient.setQueryData(bootstrapQueryKey, bootstrapPayload)
      apiClientGetMock.mockResolvedValueOnce({
        response: { status: 401 },
        data: undefined,
        error: { detail: 'Unauthorized' },
      })

      await expect(
        resyncBootstrapAfterLegalError({ code: AI_CONSENT_REQUIRED_CODE }),
      ).resolves.toBeNull()
      expect(queryClient.getQueryData(bootstrapQueryKey)).toEqual(bootstrapPayload)
    })
  })

})
