import { describe, expect, it } from 'vitest'

import { parseAppRoute } from '@/app/app-routes'
import { isProtectedRoute } from '@/app/terrain-routes'
import {
  allowsUnauthenticatedAccess,
  isPublicAuthRoute,
  resolveAuthenticatedLanding,
  routeAllowsMissingActiveMembership,
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
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: false,
      can_manage_runtime_config: false,
      can_view_team: false,
      can_manage_organization: false,
      can_create_establishment: false,
    },
    ...overrides,
  }
}

function membership(establishmentName: string, establishmentId = '33333333-3333-3333-3333-333333333333') {
  return {
    id: '22222222-2222-2222-2222-222222222222',
    establishment_id: establishmentId,
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

const ownerOrgHints = {
  chat_available: false,
  can_create_action_plan: false,
  can_create_catalog_action_plan: false,
  can_view_action_plan_catalog: false,
  can_invite: false,
  can_manage_runtime_config: false,
  can_view_team: false,
  can_manage_organization: true,
  can_create_establishment: true,
} as const

describe('resolveAuthenticatedLanding', () => {
  it('returns organization for owner with an ACTIVE membership selected', () => {
    const active = membership('Nice')
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          active_membership: active,
          memberships: [active],
          permission_hints: ownerOrgHints,
        }),
      ),
    ).toEqual({ kind: 'organization', path: '/organization' })
  })

  it('returns select-establishment for owner with multiple ACTIVE memberships without selection', () => {
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          memberships: [membership('Nice', 'est-1'), membership('Cannes', 'est-2')],
          permission_hints: ownerOrgHints,
        }),
      ),
    ).toEqual({ kind: 'establishment-selection', path: '/select-establishment' })
  })

  it('returns cross dashboard for owner with multiple ACTIVE memberships on desktop', () => {
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          memberships: [membership('Nice', 'est-1'), membership('Cannes', 'est-2')],
          permission_hints: ownerOrgHints,
        }),
        { isDesktop: true },
      ),
    ).toEqual({ kind: 'cross', path: '/cross?period=7d' })
  })

  it('returns organization for owner DRAFT-only', () => {
    const pending: PendingOnboardingMembership = {
      id: '55555555-5555-5555-5555-555555555555',
      establishment_id: '66666666-6666-6666-6666-666666666666',
      establishment_name: 'Draft Hotel',
      establishment_status: 'draft',
      organization_id: '88888888-8888-8888-8888-888888888888',
      organization_name: 'Draft Org',
      role: 'owner',
      onboarding_session_id: '77777777-7777-7777-7777-777777777777',
      can_continue_onboarding: true,
    }

    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          pending_onboarding_memberships: [pending],
          permission_hints: ownerOrgHints,
        }),
      ),
    ).toEqual({ kind: 'organization', path: '/organization' })
  })

  it('returns select-establishment for director with multiple ACTIVE without selection', () => {
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          memberships: [
            { ...membership('Nice', 'est-1'), role: 'director' as const },
            { ...membership('Cannes', 'est-2'), role: 'director' as const },
          ],
        }),
      ),
    ).toEqual({ kind: 'establishment-selection', path: '/select-establishment' })
  })

  it('returns cross dashboard for director with multiple ACTIVE memberships on desktop', () => {
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          memberships: [
            { ...membership('Nice', 'est-1'), role: 'director' as const },
            { ...membership('Cannes', 'est-2'), role: 'director' as const },
          ],
        }),
        { isDesktop: true },
      ),
    ).toEqual({ kind: 'cross', path: '/cross?period=7d' })
  })

  it('returns analytics hub on desktop when only one establishment is cross-eligible', () => {
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          memberships: [
            { ...membership('Nice', 'est-1'), role: 'manager' as const },
            { ...membership('Cannes', 'est-2'), role: 'staff' as const },
          ],
        }),
        { isDesktop: true },
      ),
    ).toEqual({ kind: 'analytics', path: '/analytics' })
  })

  it('does not return the selector on desktop for staff-only multi memberships', () => {
    const landing = resolveAuthenticatedLanding(
      bootstrap({
        memberships: [
          { ...membership('Nice', 'est-1'), role: 'staff' as const },
          { ...membership('Cannes', 'est-2'), role: 'staff' as const },
        ],
      }),
      { isDesktop: true },
    )
    expect(landing.path).not.toBe('/select-establishment')
    expect(landing).toEqual({ kind: 'empty', path: '/no-establishment' })
  })

  it('returns reporting for non-owner with ACTIVE membership selected', () => {
    const active = {
      ...membership('Nice'),
      role: 'staff' as const,
    }
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          active_membership: active,
          memberships: [active],
        }),
      ),
    ).toEqual({ kind: 'operational', path: '/reporting' })
  })

  it('returns reporting for a single active membership without selection', () => {
    expect(
      resolveAuthenticatedLanding(
        bootstrap({
          memberships: [{ ...membership('Nice'), role: 'staff' as const }],
        }),
      ),
    ).toEqual({ kind: 'operational', path: '/reporting' })
  })

  it('never lands owner without ACTIVE on /general', () => {
    const landing = resolveAuthenticatedLanding(
      bootstrap({
        permission_hints: ownerOrgHints,
      }),
    )
    expect(landing.path).not.toBe('/general')
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
              organization_id: '88888888-8888-8888-8888-888888888888',
              organization_name: 'Draft Org',
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

describe('routeAllowsMissingActiveMembership', () => {
  it('returns true for onboarding and organization routes', () => {
    expect(routeAllowsMissingActiveMembership('/pending-onboarding')).toBe(true)
    expect(routeAllowsMissingActiveMembership('/organization')).toBe(true)
    expect(routeAllowsMissingActiveMembership('/organization/establishments/est-1')).toBe(true)
    expect(routeAllowsMissingActiveMembership('/app')).toBe(false)
  })

  it('returns false for operational routes', () => {
    expect(routeAllowsMissingActiveMembership('/reporting')).toBe(false)
    expect(routeAllowsMissingActiveMembership('/general')).toBe(false)
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

  it('does not show loading for login when auth is not ready', () => {
    expect(shouldShowAuthRoutingLoading(loginRoute, { isReady: false, isAuthenticated: false })).toBe(
      false,
    )
  })

  it('shows loading for other routes when auth is not ready', () => {
    expect(shouldShowAuthRoutingLoading(rootRoute, { isReady: false, isAuthenticated: false })).toBe(
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
