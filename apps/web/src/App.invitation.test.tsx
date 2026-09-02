// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AppRoute } from '@/app/app-routes'
import { bootstrapQueryKey } from '@/features/auth/api'
import { getAuthenticatedLandingPath } from '@/features/auth/lib/authenticated-landing'
import type { BootstrapResponse, Membership } from '@/features/auth/types'
import { queryClient } from '@/lib/query-client'

const navigate = vi.fn()
const routeState = vi.hoisted(() => ({
  route: { kind: 'invitation', token: 'invite-token' } as AppRoute,
}))
const authState = vi.hoisted(() => ({
  isReady: true,
  isAuthenticated: false,
  isLoggingIn: false,
  isLoggingOut: false,
  login: vi.fn(),
  logout: vi.fn(),
  loginError: null,
  bootstrap: null as BootstrapResponse | null,
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
  serializeAppRoute: () => '/',
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
  AppShell: ({ children }: { children: React.ReactNode }) =>
    createElement('div', { 'data-testid': 'app-shell' }, children),
}))

vi.mock('@/features/invitations/pages/invitation-accept-page', () => ({
  InvitationAcceptPage: ({ onAccepted }: { onAccepted: () => void }) =>
    createElement(
      'button',
      { type: 'button', onClick: onAccepted },
      'Accept invitation',
    ),
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

function membership(): Membership {
  return {
    id: '22222222-2222-2222-2222-222222222222',
    establishment_id: '33333333-3333-3333-3333-333333333333',
    establishment_name: 'Nice',
    organization_id: '44444444-4444-4444-4444-444444444444',
    organization_name: 'Org',
    role: 'staff',
    status: 'active',
    scopes: [],
    scope_summary: {
      business_unit_count: 0,
    },
  }
}

function operationalBootstrap(): BootstrapResponse {
  const active = membership()
  return {
    authenticated: true,
    user: {
      id: '11111111-1111-1111-1111-111111111111',
      username: 'staff',
      email: 'staff@example.com',
      identity_type: 'human',
      first_name: 'Staff',
      last_name: 'Member',
      terms_version: 'cgu-v1',
      terms_accepted_at: '2026-01-01T00:00:00.000Z',
      current_terms_version: 'cgu-v1',
      needs_terms_acceptance: false,
      ai_consent_version: 'openai-v1',
      ai_processing_consented_at: '2026-01-01T00:00:00.000Z',
      current_ai_consent_version: 'openai-v1',
      needs_ai_consent: false,
    },
    memberships: [active],
    active_membership: active,
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: false,
      can_manage_runtime_config: false,
      can_view_team: false,
      can_manage_organization: false,
      can_create_establishment: false,
    },
  }
}

afterEach(() => {
  cleanup()
  navigate.mockReset()
  queryClient.clear()
  routeState.route = { kind: 'invitation', token: 'invite-token' }
  authState.isReady = true
  authState.isAuthenticated = false
  authState.bootstrap = null
  authState.hasOperationalAccess = false
  authState.pendingOnboardingMemberships = []
  authState.memberships = []
})

describe('App invitation landing', () => {
  it('navigates to the landing derived from hydrated bootstrap, not pending-onboarding', () => {
    const bootstrap = operationalBootstrap()
    const landingPath = getAuthenticatedLandingPath(bootstrap)
    queryClient.setQueryData(bootstrapQueryKey, bootstrap)
    authState.bootstrap = null

    render(createElement(App))

    fireEvent.click(screen.getByRole('button', { name: 'Accept invitation' }))

    expect(landingPath).toBe('/reporting')
    expect(navigate).toHaveBeenCalledWith('/reporting', { replace: true })
    expect(navigate).not.toHaveBeenCalledWith('/pending-onboarding', { replace: true })
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringMatching(/\/install-app/),
      expect.anything(),
    )
  })
})
