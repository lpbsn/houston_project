// @vitest-environment jsdom

import { createElement } from 'react'
import { render } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

const { configureApiClientAuth, restoreSession, fetchBootstrap } = vi.hoisted(() => ({
  configureApiClientAuth: vi.fn(),
  restoreSession: vi.fn(async () => undefined),
  fetchBootstrap: vi.fn(async () => ({
    user: { id: 'u1', username: 'owner', email: 'owner@example.com' },
    memberships: [],
    active_membership: null,
    organizations: [],
  })),
}))

vi.mock('@/api/client', () => ({
  configureApiClientAuth: (runtime: unknown) => configureApiClientAuth(runtime),
  clearApiClientAuth: vi.fn(),
}))

vi.mock('@/features/auth/api', () => ({
  bootstrapQueryKey: ['auth', 'bootstrap'],
  clearAuthState: vi.fn(),
  fetchBootstrap,
  login: vi.fn(),
  logout: vi.fn(),
  refreshAccessToken: vi.fn(),
  restoreSession,
  AuthApiError: class AuthApiError extends Error {},
}))

vi.mock('@/features/auth/session', () => ({
  getAccessToken: () => null,
  useAccessToken: () => null,
}))

import { AuthProvider } from './auth-provider'

describe('AuthProvider', () => {
  beforeEach(() => {
    configureApiClientAuth.mockClear()
    restoreSession.mockClear()
    fetchBootstrap.mockClear()
  })

  it('configures API auth runtime and resolves session on mount', async () => {
    const queryClient = createTestQueryClient()

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
})
