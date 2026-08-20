import type { AppRoute } from '@/app/app-routes'
import { getTerrainRouteConfig, usesTerrainShell } from '@/app/terrain-routes'
import {
  buildAnalyticsPatternDetailPath,
  buildAnalyticsReturnPath,
  parseAnalyticsSignalReturnContext,
  parseAnalyticsUrlState,
} from '@/features/analytics/lib/analytics-url-state'

type ResolveTerrainBackPathOptions = {
  search?: string
  now?: Date
  hasOperationalAccess?: boolean
  authenticatedLandingPath?: string | null
}

export function resolveTerrainBackPath(
  route: AppRoute,
  options: ResolveTerrainBackPathOptions = {},
): string | null {
  if (!usesTerrainShell(route)) {
    return null
  }

  const search = options.search ?? ''
  const now = options.now ?? new Date()

  if (route.kind === 'signal-detail') {
    const analyticsReturn = parseAnalyticsSignalReturnContext(search, { now })
    if (analyticsReturn) {
      return buildAnalyticsPatternDetailPath(analyticsReturn.patternId, analyticsReturn.state)
    }
  }

  if (route.kind === 'analytics-pattern-detail') {
    return buildAnalyticsReturnPath(parseAnalyticsUrlState(search, { now }))
  }

  if (
    route.kind === 'static' &&
    route.path === '/analytics' &&
    options.hasOperationalAccess === false
  ) {
    return options.authenticatedLandingPath ?? '/login'
  }

  return getTerrainRouteConfig(route).backPath ?? null
}
