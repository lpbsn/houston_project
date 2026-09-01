import type { AppRoute } from '@/app/app-routes'
import type { BootstrapResponse } from '@/features/auth/types'

import { canManageOrganizationFromBootstrapHints } from '@/features/auth/lib/bootstrap-permission-hints'
import {
  buildOnboardingUrl,
  resolvePendingLanding,
} from '@/features/auth/lib/pending-onboarding'
import { hasTrueCrossEstablishmentScope } from '@/features/navigation/lib/shared-navigation'

export const CROSS_DASHBOARD_LANDING_PATH = '/cross?period=7d'

export type AuthenticatedLanding =
  | { kind: 'operational'; path: '/reporting' }
  | { kind: 'establishment-selection'; path: '/select-establishment' }
  | { kind: 'cross'; path: typeof CROSS_DASHBOARD_LANDING_PATH }
  | { kind: 'organization'; path: '/organization' }
  | { kind: 'pending'; path: string }
  | { kind: 'empty'; path: '/no-establishment' }

export type AuthenticatedLandingContext = {
  isDesktop?: boolean
}

export function resolveAuthenticatedLanding(
  bootstrap: BootstrapResponse,
  context: AuthenticatedLandingContext = {},
): AuthenticatedLanding {
  const activeMembershipCount = bootstrap.memberships.length

  if (!bootstrap.active_membership && activeMembershipCount > 1) {
    if (context.isDesktop && hasTrueCrossEstablishmentScope(bootstrap)) {
      return { kind: 'cross', path: CROSS_DASHBOARD_LANDING_PATH }
    }
    return { kind: 'establishment-selection', path: '/select-establishment' }
  }

  if (canManageOrganizationFromBootstrapHints(bootstrap.permission_hints)) {
    return { kind: 'organization', path: '/organization' }
  }

  if (bootstrap.active_membership) {
    return { kind: 'operational', path: '/reporting' }
  }

  if (activeMembershipCount === 1) {
    return { kind: 'operational', path: '/reporting' }
  }

  const pendingLanding = resolvePendingLanding(bootstrap.pending_onboarding_memberships)

  if (pendingLanding.kind === 'onboarding') {
    return { kind: 'pending', path: buildOnboardingUrl(pendingLanding.pending) }
  }

  if (pendingLanding.kind === 'waiting' || pendingLanding.kind === 'selection') {
    return { kind: 'pending', path: '/pending-onboarding' }
  }

  return { kind: 'empty', path: '/no-establishment' }
}

export function getAuthenticatedLandingPath(
  bootstrap: BootstrapResponse | null | undefined,
  context: AuthenticatedLandingContext = {},
): string | null {
  if (!bootstrap) {
    return null
  }

  return resolveAuthenticatedLanding(bootstrap, context).path
}

export const AUTHENTICATED_LANDING_PATHS = new Set<string>([
  '/reporting',
  '/select-establishment',
  '/cross',
  '/pending-onboarding',
  '/onboarding',
  '/organization',
  '/no-establishment',
])

export function routeAllowsMissingActiveMembership(path: string): boolean {
  return (
    path === '/onboarding' ||
    path === '/pending-onboarding' ||
    path === '/select-establishment' ||
    path === '/no-establishment' ||
    path === '/organization' ||
    path.startsWith('/organization/')
  )
}

export function shouldRedirectAuthenticatedPublicRoute(route: AppRoute): boolean {
  return route.kind === 'static' && (route.path === '/' || route.path === '/login')
}

export function shouldRedirectUnauthenticatedPublicRoute(route: AppRoute): boolean {
  return route.kind === 'static' && route.path === '/'
}

export function isPublicAuthRoute(route: AppRoute): boolean {
  if (route.kind !== 'static') {
    return false
  }

  if (route.path === '/login') {
    return true
  }

  return false
}

export function allowsUnauthenticatedAccess(route: AppRoute): boolean {
  if (route.kind !== 'static') {
    return false
  }

  return route.path === '/login' || route.path === '/onboarding'
}

export function shouldShowAuthRoutingLoading(
  route: AppRoute,
  auth: { isReady: boolean; isAuthenticated: boolean },
): boolean {
  if (!auth.isReady) {
    if (route.kind === 'static' && route.path === '/login') {
      return false
    }

    return true
  }

  if (auth.isAuthenticated && shouldRedirectAuthenticatedPublicRoute(route)) {
    return true
  }

  if (!auth.isAuthenticated && shouldRedirectUnauthenticatedPublicRoute(route)) {
    return true
  }

  if (!auth.isAuthenticated && isPublicAuthRoute(route)) {
    return false
  }

  if (
    !auth.isAuthenticated &&
    route.kind === 'static' &&
    route.path === '/onboarding'
  ) {
    return false
  }

  return false
}
