import type { AppRoute } from '@/app/app-routes'
import type { BootstrapResponse } from '@/features/auth/types'

import {
  buildOnboardingUrl,
  resolvePendingLanding,
} from '@/features/auth/lib/pending-onboarding'

export type AuthenticatedLanding =
  | { kind: 'operational'; path: '/reporting' }
  | { kind: 'establishment-selection'; path: '/select-establishment' }
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

  const pendingLanding = resolvePendingLanding(bootstrap.pending_onboarding_memberships)

  if (pendingLanding.kind === 'onboarding') {
    return { kind: 'pending', path: buildOnboardingUrl(pendingLanding.pending) }
  }

  if (pendingLanding.kind === 'waiting' || pendingLanding.kind === 'selection') {
    return { kind: 'pending', path: '/pending-onboarding' }
  }

  if (activeMembershipCount === 1) {
    return { kind: 'operational', path: '/reporting' }
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

export const AUTHENTICATED_LANDING_PATHS = new Set<string>([
  '/reporting',
  '/select-establishment',
  '/pending-onboarding',
  '/onboarding',
  '/no-establishment',
])

export function routeAllowsMissingActiveMembership(path: string): boolean {
  return (
    path === '/onboarding' ||
    path === '/pending-onboarding' ||
    path === '/select-establishment' ||
    path === '/no-establishment'
  )
}

export function shouldRedirectAuthenticatedPublicRoute(route: AppRoute): boolean {
  if (route.kind === 'unknown') {
    return true
  }

  return route.kind === 'static' && (route.path === '/' || route.path === '/login')
}

export function shouldRedirectUnauthenticatedPublicRoute(route: AppRoute): boolean {
  if (route.kind === 'unknown') {
    return true
  }

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

export function shouldShowAuthRoutingLoading(
  route: AppRoute,
  auth: { isReady: boolean; isAuthenticated: boolean },
): boolean {
  if (!auth.isReady) {
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
