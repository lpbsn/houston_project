import type { AppRoute } from '@/app/app-routes'
import type { BootstrapResponse } from '@/features/auth/types'

import { canManageOrganizationFromBootstrapHints } from '@/features/auth/lib/bootstrap-permission-hints'
import {
  buildOnboardingUrl,
  resolvePendingLanding,
} from '@/features/auth/lib/pending-onboarding'
import { toRoleEnum } from '@/features/auth/lib/role'

export type AuthenticatedLanding =
  | { kind: 'operational'; path: '/reporting' }
  | { kind: 'establishment-selection'; path: '/select-establishment' }
  | { kind: 'organization'; path: '/organization' }
  | { kind: 'pending'; path: string }
  | { kind: 'empty'; path: '/no-establishment' }

export function resolveAuthenticatedLanding(
  bootstrap: BootstrapResponse,
): AuthenticatedLanding {
  if (bootstrap.active_membership) {
    return { kind: 'operational', path: '/reporting' }
  }

  const activeMembershipCount = bootstrap.memberships.length
  if (activeMembershipCount > 1) {
    return { kind: 'establishment-selection', path: '/select-establishment' }
  }

  if (activeMembershipCount === 1) {
    return { kind: 'operational', path: '/reporting' }
  }

  const canManageOrganization = canManageOrganizationFromBootstrapHints(
    bootstrap.permission_hints,
  )
  const pendingLanding = resolvePendingLanding(bootstrap.pending_onboarding_memberships)

  if (canManageOrganization) {
    if (pendingLanding.kind === 'onboarding') {
      return { kind: 'pending', path: buildOnboardingUrl(pendingLanding.pending) }
    }
    return { kind: 'organization', path: '/organization' }
  }

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
): string | null {
  if (!bootstrap) {
    return null
  }

  return resolveAuthenticatedLanding(bootstrap).path
}

export function resolveAppHubRedirectPath(
  bootstrap: BootstrapResponse | null | undefined,
): string {
  if (!bootstrap) {
    return '/login'
  }

  if (canManageOrganizationFromBootstrapHints(bootstrap.permission_hints)) {
    return '/organization'
  }

  const activeMembership = bootstrap.active_membership
  const activeRole = toRoleEnum(activeMembership?.role)
  if (activeMembership && activeRole === 'director') {
    return `/organization/establishments/${activeMembership.establishment_id}`
  }

  return getAuthenticatedLandingPath(bootstrap) ?? '/no-establishment'
}

export const AUTHENTICATED_LANDING_PATHS = new Set<string>([
  '/reporting',
  '/select-establishment',
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
    path === '/install-app' ||
    path === '/organization' ||
    path === '/app' ||
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
