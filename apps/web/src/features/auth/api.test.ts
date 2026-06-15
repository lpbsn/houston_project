import { beforeEach, describe, expect, it, vi } from 'vitest'

import { queryClient } from '@/lib/query-client'

const { withAuthRetryMock, clearAccessTokenMock, setAccessTokenMock, getAccessTokenMock } =
  vi.hoisted(() => ({
    withAuthRetryMock: vi.fn(),
    clearAccessTokenMock: vi.fn(),
    setAccessTokenMock: vi.fn(),
    getAccessTokenMock: vi.fn(),
  }))

vi.mock('@/api/client', () => ({
  apiClient: {},
  withAuthRetry: (...args: unknown[]) => withAuthRetryMock(...args),
}))

vi.mock('./csrf', () => ({
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
  switchEstablishment,
} from '@/features/auth/api'

const bootstrapPayload = {
  authenticated: true,
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

describe('auth api cache isolation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    queryClient.clear()
    withAuthRetryMock.mockImplementation(async (execute: (token: string | null) => Promise<unknown>) =>
      execute('access-token'),
    )
  })

  it('purges non-auth queries when switching establishment', async () => {
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

    withAuthRetryMock.mockResolvedValueOnce({
      response: { status: 200 },
      data: bootstrapPayload,
      error: undefined,
    })

    const result = await switchEstablishment({ establishment_id: 'est-b' })

    expect(result).toEqual(bootstrapPayload)
    expect(queryClient.getQueryData(['signals', 'feed', 'est-a', 'general', {}])).toBeUndefined()
    expect(queryClient.getQueryData(['workspace', 'summary', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['reporting', 'kpi', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['onboarding', 'sessions', 's-1'])).toBeUndefined()
    expect(queryClient.getQueryData(['chat', 'status', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['chat', 'conversations', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(bootstrapQueryKey)).toEqual(bootstrapPayload)
  })

  it('clears the entire query cache on clearAuthState', () => {
    queryClient.setQueryData(['actions', 'detail', 'est-a', 'act-1'], { id: 'act-1' })
    queryClient.setQueryData(['chat', 'conversations', 'est-a'], { items: [] })
    queryClient.setQueryData(['reporting', 'kpi', 'est-a'], { kpi: 1 })
    queryClient.setQueryData(bootstrapQueryKey, bootstrapPayload)

    clearAuthState()

    expect(clearAccessTokenMock).toHaveBeenCalledOnce()
    expect(queryClient.getQueryData(['actions', 'detail', 'est-a', 'act-1'])).toBeUndefined()
    expect(queryClient.getQueryData(['chat', 'conversations', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['reporting', 'kpi', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(bootstrapQueryKey)).toBeUndefined()
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0)
  })
})
