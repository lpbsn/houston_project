import type { AppRoute } from '@/app/app-routes'

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

const CROSS_PAGES = new Set(['reporting', 'signals', 'execution', 'chat', 'settings'])
const ESTABLISHMENT_PAGES = new Set([
  'reporting',
  'signals',
  'execution',
  'chat',
  'general',
  'settings',
])

export type TerrainScope =
  | { type: 'cross' }
  | { type: 'establishment'; establishmentId: string }

export type ScopedTerrainPage =
  | 'dashboard'
  | 'reporting'
  | 'signals'
  | 'execution'
  | 'chat'
  | 'general'
  | 'settings'

export type ScopedTerrainRoute = {
  kind: 'scoped-terrain'
  scope: TerrainScope
  page: ScopedTerrainPage
}

export function isValidUuid(value: string): boolean {
  return UUID_PATTERN.test(value)
}

export function terrainScopeKey(scope: TerrainScope | undefined): string {
  if (!scope) {
    return 'session'
  }
  if (scope.type === 'cross') {
    return 'cross'
  }
  return `establishment:${scope.establishmentId}`
}

export function serializeScopedTerrainPath(
  scope: TerrainScope,
  page: ScopedTerrainPage = 'dashboard',
): string {
  if (scope.type === 'cross') {
    return page === 'dashboard' ? '/cross' : `/cross/${page}`
  }
  return page === 'dashboard'
    ? `/e/${scope.establishmentId}`
    : `/e/${scope.establishmentId}/${page}`
}

export function serializeScopedSignalDetailPath(scope: TerrainScope, signalId: string): string {
  if (scope.type === 'cross') {
    return `/cross/signals/${signalId}`
  }
  return `/e/${scope.establishmentId}/signals/${signalId}`
}

export function serializeScopedExecutionDetailPath(
  scope: TerrainScope,
  executionId: string,
): string {
  if (scope.type === 'cross') {
    return `/cross/execution/${executionId}`
  }
  return `/e/${scope.establishmentId}/execution/${executionId}`
}

function parsePageSegment(
  segment: string,
  allowed: Set<string>,
): ScopedTerrainPage | null {
  if (allowed.has(segment)) {
    return segment as ScopedTerrainPage
  }
  return null
}

export function parseScopedTerrainRoute(pathname: string): AppRoute | null {
  if (pathname === '/cross') {
    return { kind: 'scoped-terrain', scope: { type: 'cross' }, page: 'dashboard' }
  }

  const crossSignalDetail = pathname.match(/^\/cross\/signals\/([^/]+)$/)
  if (crossSignalDetail?.[1] && isValidUuid(crossSignalDetail[1])) {
    return {
      kind: 'signal-detail',
      signalId: crossSignalDetail[1],
      scope: { type: 'cross' },
    }
  }

  const crossExecutionDetail = pathname.match(/^\/cross\/execution\/([^/]+)$/)
  if (crossExecutionDetail?.[1] && isValidUuid(crossExecutionDetail[1])) {
    return {
      kind: 'action-plan-execution-detail',
      executionId: crossExecutionDetail[1],
      scope: { type: 'cross' },
    }
  }

  const crossPage = pathname.match(/^\/cross\/([^/]+)$/)
  if (crossPage?.[1]) {
    const page = parsePageSegment(crossPage[1], CROSS_PAGES)
    if (page) {
      return { kind: 'scoped-terrain', scope: { type: 'cross' }, page }
    }
  }

  const establishmentMatch = pathname.match(/^\/e\/([^/]+)(?:\/([^/]+))?(?:\/([^/]+))?$/)
  if (!establishmentMatch?.[1] || !isValidUuid(establishmentMatch[1])) {
    return null
  }

  const establishmentId = establishmentMatch[1]
  const pageSegment = establishmentMatch[2]
  const detailId = establishmentMatch[3]
  const scope: TerrainScope = { type: 'establishment', establishmentId }

  if (!pageSegment) {
    return { kind: 'scoped-terrain', scope, page: 'dashboard' }
  }

  if (pageSegment === 'signals' && detailId && isValidUuid(detailId)) {
    return { kind: 'signal-detail', signalId: detailId, scope }
  }

  if (pageSegment === 'execution' && detailId && isValidUuid(detailId)) {
    return {
      kind: 'action-plan-execution-detail',
      executionId: detailId,
      scope,
    }
  }

  if (detailId) {
    return null
  }

  const page = parsePageSegment(pageSegment, ESTABLISHMENT_PAGES)
  if (!page) {
    return null
  }

  return { kind: 'scoped-terrain', scope, page }
}
