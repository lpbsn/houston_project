// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AppRoute } from '@/app/app-routes'

const navigate = vi.fn()
const appShellRenderCount = vi.hoisted(() => ({ value: 0 }))
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

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    route: routeState.route,
    navigate,
  }),
}))

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

vi.mock('@/components/app-shell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => {
    appShellRenderCount.value += 1
    return createElement('div', { 'data-testid': 'app-shell' }, children)
  },
}))

vi.mock('@/components/layout/pwa-update-banner', () => ({
  PwaUpdateBanner: () => createElement('div', { 'data-testid': 'pwa-update-banner' }),
}))

vi.mock('@/features/onboarding/pages/onboarding-page', () => ({
  OnboardingPage: () => createElement('div', { 'data-testid': 'onboarding-page-stub' }),
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
  appShellRenderCount.value = 0
  routeState.route = { kind: 'static', path: '/onboarding' }
  authState.isReady = true
  authState.isAuthenticated = false
  authState.hasOperationalAccess = false
  authState.pendingOnboardingMemberships = []
  authState.bootstrap = null
})

describe('App /onboarding routing', () => {
  it('renders onboarding outside AppShell', () => {
    render(createElement(App))

    expect(screen.getByTestId('onboarding-shell')).toBeTruthy()
    expect(screen.getByTestId('onboarding-page-stub')).toBeTruthy()
    expect(screen.queryByTestId('app-shell')).toBeNull()
    expect(appShellRenderCount.value).toBe(0)
  })
})
