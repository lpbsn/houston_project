// @vitest-environment jsdom

import type { QueryClient } from '@tanstack/react-query'
import { createElement } from 'react'
import { act, render } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { bootstrapQueryKey } from '@/features/auth/api'
import type { BootstrapResponse } from '@/features/auth/types'
import { queryClient } from '@/lib/query-client'

const { configureApiClientAuth, restoreSession, fetchBootstrap, logout, sessionState } = vi.hoisted(
  () => ({
    configureApiClientAuth: vi.fn(),
    restoreSession: vi.fn(async () => undefined),
    fetchBootstrap: vi.fn(async () => ({
      user: { id: 'u1', username: 'owner', email: 'owner@example.com' },
      memberships: [],
      active_membership: null,
      organizations: [],
    })),
    logout: vi.fn(async () => undefined),
    sessionState: { accessToken: 'access-token' as string | null },
  }),
)

vi.mock('@/api/client', () => ({
  configureApiClientAuth: (runtime: unknown) => configureApiClientAuth(runtime),
  clearApiClientAuth: vi.fn(),
}))

vi.mock('@/features/auth/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/auth/api')>()
  return {
    ...actual,
    fetchBootstrap,
    login: vi.fn(),
    logout,
    refreshAccessToken: vi.fn(),
    restoreSession,
    AuthApiError: class AuthApiError extends Error {},
  }
})

vi.mock('@/features/auth/session', () => ({
  clearAccessToken: vi.fn(() => {
    sessionState.accessToken = null
  }),
  getAccessToken: () => sessionState.accessToken,
  setAccessToken: vi.fn((token: string) => {
    sessionState.accessToken = token
  }),
  useAccessToken: () => sessionState.accessToken,
}))

import { AuthProvider, useAuth } from './auth-provider'

function expectBootstrapSafeAfterLogout(client: QueryClient) {
  const bootstrap = client.getQueryData<BootstrapResponse>(bootstrapQueryKey)

  if (bootstrap === undefined) {
    return
  }

  expect(bootstrap.user ?? null).toBeNull()
  expect(bootstrap.active_membership ?? null).toBeNull()
  expect(bootstrap.memberships ?? []).toEqual([])
  expect(bootstrap.authenticated).not.toBe(true)
  expect(bootstrap.permission_hints ?? {}).toEqual({})
}

describe('AuthProvider', () => {
  beforeEach(() => {
    configureApiClientAuth.mockClear()
    restoreSession.mockClear()
    fetchBootstrap.mockClear()
    logout.mockClear()
    queryClient.clear()
    sessionState.accessToken = 'access-token'
  })

  it('configures API auth runtime and resolves session on mount', async () => {
    render(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(AuthProvider, null, createElement('div', { 'data-testid': 'child' })),
      ),
    )

    expect(configureApiClientAuth).toHaveBeenCalledTimes(1)
    expect(configureApiClientAuth.mock.calls[0]?.[0]).toMatchObject({
      getAccessToken: expect.any(Function),
      refreshAccessToken: expect.any(Function),
      clearAuth: expect.any(Function),
    })

    await vi.waitFor(() => {
      expect(restoreSession).toHaveBeenCalled()
    })
  })

  it('does not retain authenticated or tenant cache after logout', async () => {
    queryClient.setQueryData(['signals', 'feed', 'est-a', 'general', {}], { items: ['stale'] })
    queryClient.setQueryData(['workspace', 'summary', 'est-a'], { name: 'A' })
    queryClient.setQueryData(['workspace', 'memberships', 'est-a'], [{ id: 'm1' }])
    queryClient.setQueryData(['reporting', 'kpi', 'est-a'], { kpi: 1 })
    queryClient.setQueryData(['onboarding', 'sessions', 's-1'], { id: 's-1' })
    queryClient.setQueryData(bootstrapQueryKey, {
      authenticated: true,
      user: { id: 'u1', username: 'owner', email: 'owner@example.com' },
      memberships: [
        {
          id: 'm1',
          establishment_id: 'est-a',
          establishment_name: 'Establishment A',
          role: 'manager',
          status: 'active',
        },
      ],
      active_membership: {
        id: 'm1',
        establishment_id: 'est-a',
        establishment_name: 'Establishment A',
        role: 'manager',
        status: 'active',
      },
      pending_onboarding_memberships: [],
      permission_hints: { can_manage_signals: true },
    })

    let logoutHandler: (() => Promise<void>) | null = null
    let authSnapshot: {
      isAuthenticated: boolean
      user: BootstrapResponse['user'] | null
      activeMembership: BootstrapResponse['active_membership'] | null
      memberships: BootstrapResponse['memberships']
    } | null = null

    function LogoutProbe() {
      const auth = useAuth()
      logoutHandler = auth.logout
      authSnapshot = {
        isAuthenticated: auth.isAuthenticated,
        user: auth.user,
        activeMembership: auth.activeMembership,
        memberships: auth.memberships,
      }
      return createElement('div', { 'data-testid': 'child' })
    }

    render(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(AuthProvider, null, createElement(LogoutProbe)),
      ),
    )

    await vi.waitFor(() => {
      expect(logoutHandler).not.toBeNull()
    })

    await act(async () => {
      await logoutHandler!()
    })

    expect(logout).toHaveBeenCalledOnce()
    expect(queryClient.getQueryData(['signals', 'feed', 'est-a', 'general', {}])).toBeUndefined()
    expect(queryClient.getQueryData(['workspace', 'summary', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['workspace', 'memberships', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['reporting', 'kpi', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['onboarding', 'sessions', 's-1'])).toBeUndefined()
    expectBootstrapSafeAfterLogout(queryClient)

    expect(authSnapshot).not.toBeNull()
    expect(authSnapshot!.isAuthenticated).toBe(false)
    expect(authSnapshot!.user).toBeNull()
    expect(authSnapshot!.activeMembership).toBeNull()
    expect(authSnapshot!.memberships).toEqual([])
  })
})
