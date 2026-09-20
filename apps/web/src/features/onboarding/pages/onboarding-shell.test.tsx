// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AppRoute } from '@/app/app-routes'

const navigate = vi.fn()
const routeState = vi.hoisted(() => ({
  route: { kind: 'static', path: '/onboarding' } as AppRoute,
}))
const authState = vi.hoisted(() => ({
  isReady: true,
  isAuthenticated: false,
  isLoggingIn: false,
  isLoggingOut: false,
  login: vi.fn(),
  logout: vi.fn(),
  loginError: null,
  bootstrap: null,
  hasOperationalAccess: false,
  pendingOnboardingMemberships: [] as unknown[],
  memberships: [] as unknown[],
  activeMembership: null,
}))

vi.mock('@/app/app-routes', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/app-routes')>()
  return {
    ...actual,
    useAppRoute: () => ({
      route: routeState.route,
      navigate,
      search: window.location.search,
    }),
  }
})

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState,
}))

vi.mock('@/app/terrain-routes', () => ({
  getTerrainContentKey: vi.fn(),
  getTerrainRouteConfig: vi.fn(),
  isProtectedRoute: () => false,
  requiresActiveMembership: () => false,
  resolveTerrainTopbarShowBottomBorder: vi.fn(),
  usesTerrainShell: () => false,
}))

vi.mock('@/features/chat/hooks', () => ({
  useChatAvailability: () => ({
    isNavVisible: false,
    statusResolved: true,
    isRuntimeAvailable: false,
  }),
  useChatConversationsQuery: () => ({ data: { items: [] } }),
}))

vi.mock('framer-motion', () => ({
  motion: {
    main: ({ children, ...props }: React.ComponentProps<'main'>) =>
      createElement('main', props, children),
  },
  useReducedMotion: () => true,
}))

import App from '@/App'

afterEach(() => {
  cleanup()
  navigate.mockReset()
  routeState.route = { kind: 'static', path: '/onboarding' }
  authState.isReady = true
  authState.isAuthenticated = false
  authState.hasOperationalAccess = false
  authState.pendingOnboardingMemberships = []
  authState.bootstrap = null
})

describe('App /onboarding routing', () => {
  it('redirects former wizard links to login', () => {
    render(createElement(App))
    expect(navigate).toHaveBeenCalledWith('/login', { replace: true })
  })
})
