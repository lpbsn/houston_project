// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AppRoute } from '@/app/app-routes'

const navigate = vi.fn()
const pwaBannerRenderCount = vi.hoisted(() => ({ value: 0 }))
const appShellRenderCount = vi.hoisted(() => ({ value: 0 }))
const routeState = vi.hoisted(() => ({
  route: { kind: 'static', path: '/login' } as AppRoute,
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
}))

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    route: routeState.route,
    navigate,
    search: window.location.search,
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
  PwaUpdateBanner: () => {
    pwaBannerRenderCount.value += 1
    return createElement('div', { 'data-testid': 'pwa-update-banner' })
  },
}))

vi.mock('@/features/auth/components/login-form', () => ({
  LoginForm: () => createElement('div', { 'data-testid': 'login-form-stub' }, 'Se connecter'),
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

function resetAuthState() {
  authState.isReady = true
  authState.isAuthenticated = false
  authState.isLoggingIn = false
  authState.isLoggingOut = false
  authState.loginError = null
  authState.bootstrap = null
  authState.hasOperationalAccess = false
  authState.pendingOnboardingMemberships = []
  authState.memberships = []
}

afterEach(() => {
  cleanup()
  navigate.mockReset()
  pwaBannerRenderCount.value = 0
  appShellRenderCount.value = 0
  routeState.route = { kind: 'static', path: '/login' }
  resetAuthState()
})

describe('App /login routing', () => {
  it('renders LoginPage without AppShell and a single PwaUpdateBanner', () => {
    render(createElement(App))

    expect(screen.getByTestId('login-page')).toBeTruthy()
    expect(screen.queryByTestId('app-shell')).toBeNull()
    expect(screen.queryByText('Welcome back')).toBeNull()
    expect(screen.queryByText('houston')).toBeNull()
    expect(screen.getAllByTestId('pwa-update-banner')).toHaveLength(1)
    expect(appShellRenderCount.value).toBe(0)
    expect(pwaBannerRenderCount.value).toBe(1)
  })

  it('renders LoginPage session-restore UI when auth is not ready', () => {
    authState.isReady = false

    render(createElement(App))

    expect(screen.getByTestId('login-page')).toBeTruthy()
    expect(screen.getByText('Restauration de votre session…')).toBeTruthy()
    expect(screen.queryByText('Chargement de votre session…')).toBeNull()
    expect(screen.queryByText('Se connecter')).toBeNull()
    expect(screen.queryByTestId('login-form-stub')).toBeNull()
  })

  it('renders AuthRoutingLoading for other routes when auth is not ready', () => {
    authState.isReady = false
    routeState.route = { kind: 'static', path: '/reporting' }

    render(createElement(App))

    expect(screen.getByText('Chargement de votre session…')).toBeTruthy()
    expect(screen.queryByTestId('login-page')).toBeNull()
  })

  it('renders AuthRoutingLoading for authenticated login while redirect is pending', () => {
    authState.isReady = true
    authState.isAuthenticated = true
    authState.bootstrap = {
      active_membership: { id: 'membership-1' },
      memberships: [{ id: 'membership-1' }],
      pending_onboarding_memberships: [],
    }

    render(createElement(App))

    expect(screen.getByText('Chargement de votre session…')).toBeTruthy()
    expect(screen.queryByTestId('login-page')).toBeNull()
  })
})
