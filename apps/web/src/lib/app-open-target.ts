import { parseAppRoute, serializeAppRoute, type AppRoute } from '@/app/app-routes'
import {
  allowsUnauthenticatedAccess,
  shouldRedirectUnauthenticatedPublicRoute,
} from '@/features/auth/lib/authenticated-landing'
import { getPublicAppOrigin } from '@/lib/runtime'

export type AppOpenTarget = {
  href: string
  establishmentId?: string
}

export type AppOpenSession = {
  getActiveEstablishmentId: () => string | null
  switchEstablishment: (establishmentId: string) => Promise<void>
  navigate: (href: string, options?: { replace?: boolean }) => void
}

export function isRelativeAppPath(url: string): boolean {
  return url.startsWith('/') && !url.startsWith('//') && !url.includes('://')
}

function readEstablishmentIdParam(params: URLSearchParams): string | undefined {
  const value = params.get('establishment_id')?.trim()
  return value ? value : undefined
}

function searchWithoutEstablishmentId(search: string): string {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  params.delete('establishment_id')
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export function isPublicAppOpenTarget(target: AppOpenTarget): boolean {
  const route = parseAppRoute(target.href)
  return route.kind === 'invitation' || allowsUnauthenticatedAccess(route)
}

export function isPendingDestinationHref(href: string): boolean {
  if (!isRelativeAppPath(href)) {
    return false
  }

  const route = parseAppRoute(href)
  if (route.kind === 'unknown' || route.kind === 'invitation') {
    return false
  }
  if (allowsUnauthenticatedAccess(route) || shouldRedirectUnauthenticatedPublicRoute(route)) {
    return false
  }

  return true
}

export function parseExternalAppUrl(
  raw: string,
  publicOrigin: string = getPublicAppOrigin(),
): AppOpenTarget | null {
  let expected: URL
  let incoming: URL
  try {
    expected = new URL(publicOrigin)
    incoming = new URL(raw)
  } catch {
    return null
  }

  if (expected.protocol !== 'https:' || incoming.protocol !== 'https:') {
    return null
  }
  if (incoming.origin !== expected.origin) {
    return null
  }

  const params = new URLSearchParams(incoming.search)
  const establishmentId = readEstablishmentIdParam(params)
  params.delete('establishment_id')
  const qs = params.toString()
  const href = `${incoming.pathname}${qs ? `?${qs}` : ''}`
  const route = parseAppRoute(href)
  if (route.kind === 'unknown') {
    return null
  }

  return establishmentId ? { href, establishmentId } : { href }
}

export function parseAppOpenTargetFromLocation(route: AppRoute, search: string): AppOpenTarget | null {
  if (route.kind === 'unknown' || route.kind === 'invitation') {
    return null
  }
  if (allowsUnauthenticatedAccess(route) || shouldRedirectUnauthenticatedPublicRoute(route)) {
    return null
  }
  if (route.kind === 'static' && route.path === '/select-establishment') {
    return null
  }

  const pathname = serializeAppRoute(route).split('?')[0] ?? '/'
  const href = `${pathname}${searchWithoutEstablishmentId(search)}`
  if (!isPendingDestinationHref(href)) {
    return null
  }

  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  const establishmentId = readEstablishmentIdParam(params)
  return establishmentId ? { href, establishmentId } : { href }
}

export function parsePendingAppOpenFromSearch(search: string): AppOpenTarget | null {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  const next = params.get('next')
  if (!next || !isPendingDestinationHref(next)) {
    return null
  }

  const establishmentId = readEstablishmentIdParam(params)
  return establishmentId ? { href: next, establishmentId } : { href: next }
}

export function buildLoginRedirectHref(target: AppOpenTarget): string {
  return buildAuthCarryHref('/login', target)
}

export function buildSelectEstablishmentRedirectHref(target: AppOpenTarget): string {
  return buildAuthCarryHref('/select-establishment', target)
}

function buildAuthCarryHref(path: '/login' | '/select-establishment', target: AppOpenTarget): string {
  const params = new URLSearchParams()
  params.set('next', target.href)
  if (target.establishmentId) {
    params.set('establishment_id', target.establishmentId)
  }
  return `${path}?${params.toString()}`
}

export async function applyAppOpenTarget(
  target: AppOpenTarget,
  session: AppOpenSession,
  options?: { replace?: boolean },
): Promise<void> {
  if (target.establishmentId && session.getActiveEstablishmentId() !== target.establishmentId) {
    await session.switchEstablishment(target.establishmentId)
  }
  session.navigate(target.href, { replace: options?.replace ?? true })
}

export function resolveSelectEstablishmentHintTarget(
  search: string,
  memberships: ReadonlyArray<{ establishment_id: string }>,
): AppOpenTarget | null {
  const pending = parsePendingAppOpenFromSearch(search)
  if (!pending?.establishmentId) {
    return null
  }
  if (!memberships.some((membership) => membership.establishment_id === pending.establishmentId)) {
    return null
  }
  return pending
}

export function resolveSelectEstablishmentResumeHref(
  pending: AppOpenTarget | null,
  selectedEstablishmentId: string,
): string {
  if (!pending) {
    return '/reporting'
  }
  if (pending.establishmentId && pending.establishmentId !== selectedEstablishmentId) {
    return '/reporting'
  }
  return pending.href
}
