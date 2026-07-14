// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const navigate = vi.fn()
const pwaBannerRenderCount = vi.hoisted(() => ({ value: 0 }))
const appShellRenderCount = vi.hoisted(() => ({ value: 0 }))

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    route: { kind: 'static', path: '/login' },
    navigate,
  }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    isReady: true,
    isAuthenticated: false,
    isLoggingIn: false,
    isLoggingOut: false,
    login: vi.fn(),
    logout: vi.fn(),
    loginError: null,
    bootstrap: null,
    hasOperationalAccess: false,
    pendingOnboardingMemberships: [],
  }),
}))

vi.mock('@/features/auth/lib/authenticated-landing', () => ({
  allowsUnauthenticatedAccess: () => true,
  getAuthenticatedLandingPath: () => null,
  routeAllowsMissingActiveMembership: () => false,
  shouldRedirectAuthenticatedPublicRoute: () => false,
  shouldRedirectUnauthenticatedPublicRoute: () => false,
  shouldShowAuthRoutingLoading: () => false,
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
  PwaUpdateBanner: () => {
    pwaBannerRenderCount.value += 1
    return createElement('div', { 'data-testid': 'pwa-update-banner' })
  },
}))

vi.mock('@/features/auth/pages/login-page', () => ({
  LoginPage: () => createElement('div', { 'data-testid': 'login-page-mock' }, 'LoginPage'),
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

import App from './App'

afterEach(() => {
  cleanup()
  navigate.mockReset()
  pwaBannerRenderCount.value = 0
  appShellRenderCount.value = 0
})

describe('App /login routing', () => {
  it('renders LoginPage without AppShell and a single PwaUpdateBanner', () => {
    render(createElement(App))

    expect(screen.getByTestId('login-page-mock')).toBeTruthy()
    expect(screen.queryByTestId('app-shell')).toBeNull()
    expect(screen.queryByText('Welcome back')).toBeNull()
    expect(screen.queryByText('houston')).toBeNull()
    expect(screen.getAllByTestId('pwa-update-banner')).toHaveLength(1)
    expect(appShellRenderCount.value).toBe(0)
    expect(pwaBannerRenderCount.value).toBe(1)
  })
})
