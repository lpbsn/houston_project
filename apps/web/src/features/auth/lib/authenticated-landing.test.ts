import { describe, expect, it } from 'vitest'

import { parseAppRoute } from '@/app/app-routes'
import { isProtectedRoute } from '@/app/terrain-routes'
import {
  allowsUnauthenticatedAccess,
  isPublicAuthRoute,
  resolveAuthenticatedLanding,
  shouldRedirectAuthenticatedPublicRoute,
  shouldRedirectUnauthenticatedPublicRoute,
  shouldShowAuthRoutingLoading,
} from '@/features/auth/lib/authenticated-landing'
import type { BootstrapResponse } from '@/features/auth/types'
import type { PendingOnboardingMembership } from '@/features/auth/lib/pending-onboarding'

function bootstrap(
  overrides: Partial<BootstrapResponse> & {
    pending_onboarding_memberships?: PendingOnboardingMembership[]
  } = {},
): BootstrapResponse {
  return {
    authenticated: true,
    user: {
      id: '11111111-1111-1111-1111-111111111111',
      username: 'owner',
      email: 'owner@example.com',
      identity_type: 'owner',
    },
    memberships: [],
    active_membership: null,
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: false,
      can_create_action: false,
      can_invite: false,
      can_manage_runtime_config: false,
    },
    ...overrides,
  }
}

function membership(establishmentName: string) {
  return {
    id: '22222222-2222-2222-2222-222222222222',
    establishment_id: '33333333-3333-3333-3333-333333333333',
    establishment_name: establishmentName,
    organization_id: '44444444-4444-4444-4444-444444444444',
    organization_name: 'Org',
    role: 'owner' as const,
    status: 'active' as const,
    scopes: [],
    scope_summary: {
      business_unit_count: 0,
    },
  }
}

describe('resolveAuthenticatedLanding', () => {
  it('returns reporting when active membership is selected', () => {
    const active = membership('Nice')
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          active_membership: active,
          memberships: [active],
        }),
      ),
    ).toEqual({ kind: 'operational', path: '/reporting' })
  })

  it('returns select-establishment for multiple active memberships without selection', () => {
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          memberships: [membership('Nice'), membership('Cannes')],
        }),
      ),
    ).toEqual({ kind: 'establishment-selection', path: '/select-establishment' })
  })

  it('returns onboarding url for a single owner pending draft', () => {
    const pending: PendingOnboardingMembership = {
      id: '55555555-5555-5555-5555-555555555555',
      establishment_id: '66666666-6666-6666-6666-666666666666',
      establishment_name: 'Draft Hotel',
      establishment_status: 'draft',
      role: 'owner',
      onboarding_session_id: '77777777-7777-7777-7777-777777777777',
      can_continue_onboarding: true,
    }

    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          pending_onboarding_memberships: [pending],
        }),
      ),
    ).toEqual({
      kind: 'pending',
      path: '/onboarding?establishmentId=66666666-6666-6666-6666-666666666666&sessionId=77777777-7777-7777-7777-777777777777',
    })
  })

  it('returns pending-onboarding for director waiting state', () => {
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          pending_onboarding_memberships: [
            {
              id: '55555555-5555-5555-5555-555555555555',
              establishment_id: '66666666-6666-6666-6666-666666666666',
              establishment_name: 'Draft Hotel',
              establishment_status: 'draft',
              role: 'director',
              onboarding_session_id: '77777777-7777-7777-7777-777777777777',
              can_continue_onboarding: false,
            },
          ],
        }),
      ),
    ).toEqual({ kind: 'pending', path: '/pending-onboarding' })
  })

  it('returns no-establishment when nothing is available', () => {
    expect(resolveAuthenticatedLanding(bootstrap())).toEqual({
      kind: 'empty',
      path: '/no-establishment',
    })
  })
})

describe('shouldRedirectAuthenticatedPublicRoute', () => {
  it('returns true for root and login only', () => {
    expect(shouldRedirectAuthenticatedPublicRoute({ kind: 'static', path: '/' })).toBe(true)
    expect(shouldRedirectAuthenticatedPublicRoute({ kind: 'static', path: '/login' })).toBe(true)
    expect(shouldRedirectAuthenticatedPublicRoute({ kind: 'unknown', pathname: '/foo' })).toBe(
      false,
    )
  })

  it('returns false for operational routes', () => {
    expect(
      shouldRedirectAuthenticatedPublicRoute({ kind: 'static', path: '/reporting' }),
    ).toBe(false)
    expect(
      shouldRedirectAuthenticatedPublicRoute({ kind: 'static', path: '/onboarding' }),
    ).toBe(false)
  })
})

describe('shouldRedirectUnauthenticatedPublicRoute', () => {
  it('returns true for root only', () => {
    expect(shouldRedirectUnauthenticatedPublicRoute({ kind: 'static', path: '/' })).toBe(true)
    expect(shouldRedirectUnauthenticatedPublicRoute({ kind: 'unknown', pathname: '/foo' })).toBe(
      false,
    )
  })

  it('returns false for login', () => {
    expect(
      shouldRedirectUnauthenticatedPublicRoute({ kind: 'static', path: '/login' }),
    ).toBe(false)
  })
})

describe('isPublicAuthRoute', () => {
  it('returns true only for login', () => {
    expect(isPublicAuthRoute({ kind: 'static', path: '/login' })).toBe(true)
    expect(isPublicAuthRoute({ kind: 'static', path: '/onboarding' })).toBe(false)
    expect(isPublicAuthRoute({ kind: 'static', path: '/' })).toBe(false)
    expect(isPublicAuthRoute({ kind: 'unknown', pathname: '/login' })).toBe(false)
  })
})

describe('allowsUnauthenticatedAccess', () => {
  it('returns true for login and onboarding', () => {
    expect(allowsUnauthenticatedAccess({ kind: 'static', path: '/login' })).toBe(true)
    expect(allowsUnauthenticatedAccess({ kind: 'static', path: '/onboarding' })).toBe(true)
  })

  it('returns false for protected and unknown routes', () => {
    expect(allowsUnauthenticatedAccess({ kind: 'static', path: '/reporting' })).toBe(false)
    expect(allowsUnauthenticatedAccess({ kind: 'static', path: '/pending-onboarding' })).toBe(
      false,
    )
    expect(allowsUnauthenticatedAccess({ kind: 'unknown', pathname: '/onboarding' })).toBe(false)
  })

  it('does not redirect unauthenticated onboarding to login', () => {
    const route = { kind: 'static' as const, path: '/onboarding' as const }
    const isAuthenticated = false

    expect(
      isProtectedRoute(route) && !isAuthenticated && !allowsUnauthenticatedAccess(route),
    ).toBe(false)
  })
})

describe('shouldShowAuthRoutingLoading', () => {
  const loginRoute = { kind: 'static' as const, path: '/login' as const }
  const rootRoute = { kind: 'static' as const, path: '/' as const }
  const onboardingRoute = { kind: 'static' as const, path: '/onboarding' as const }
  const unknownRoute = { kind: 'unknown' as const, pathname: '/foo' }

  it('shows loading when auth is not ready', () => {
    expect(shouldShowAuthRoutingLoading(loginRoute, { isReady: false, isAuthenticated: false })).toBe(
      true,
    )
  })

  it('does not show loading for login when unauthenticated and ready', () => {
    expect(shouldShowAuthRoutingLoading(loginRoute, { isReady: true, isAuthenticated: false })).toBe(
      false,
    )
  })

  it('shows loading for login when authenticated and ready (redirect pending)', () => {
    expect(shouldShowAuthRoutingLoading(loginRoute, { isReady: true, isAuthenticated: true })).toBe(
      true,
    )
  })

  it('does not show loading for onboarding when unauthenticated and ready', () => {
    expect(
      shouldShowAuthRoutingLoading(onboardingRoute, { isReady: true, isAuthenticated: false }),
    ).toBe(false)
  })

  it('shows loading for root when unauthenticated and ready', () => {
    expect(shouldShowAuthRoutingLoading(rootRoute, { isReady: true, isAuthenticated: false })).toBe(
      true,
    )
  })

  it('does not show loading for unknown when unauthenticated and ready', () => {
    expect(
      shouldShowAuthRoutingLoading(unknownRoute, { isReady: true, isAuthenticated: false }),
    ).toBe(false)
  })

  it('treats parseAppRoute login with query as login for loading policy', () => {
    const route = parseAppRoute('/login?foo=bar')
    expect(route).toEqual({ kind: 'static', path: '/login' })
    expect(shouldShowAuthRoutingLoading(route, { isReady: true, isAuthenticated: false })).toBe(
      false,
    )
  })
})
