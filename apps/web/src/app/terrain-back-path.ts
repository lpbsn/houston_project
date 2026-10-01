import { getHrefSearch, type AppHistory } from '@/app/app-history'
import { parseAppRoute, type AppRoute } from '@/app/app-routes'
import { getTerrainContentKey, getTerrainRouteConfig, usesTerrainShell } from '@/app/terrain-routes'
import type { TerrainScope } from '@/app/scoped-terrain'
import {
  buildAnalyticsPatternDetailPath,
  buildAnalyticsReturnPath,
  buildAnalyticsSignalDetailPath,
  parseAnalyticsSignalReturnContext,
  parseAnalyticsUrlState,
} from '@/features/analytics/lib/analytics-url-state'
import {
  appendExecutionFeedSearch,
  executionFeedHref,
  parseExecutionFeedSearch,
} from '@/features/execution/lib/execution-feed-url-state'
import {
  historySearchWithoutReturnFlag,
  isHistoryReturnSearch,
} from '@/features/history/lib/history-url-state'
import { explicitTerrainScope } from '@/features/navigation/lib/scoped-desktop-navigation'
import { dismissTopNativeOverlay } from '@/lib/native-overlay-dismiss'

type ResolveTerrainBackPathOptions = {
  search?: string
  now?: Date
  hasOperationalAccess?: boolean
  authenticatedLandingPath?: string | null
}

function historyReturnPath(route: AppRoute, search: string): string | null {
  if (!isHistoryReturnSearch(search)) {
    return null
  }
  if (route.kind !== 'signal-detail' && route.kind !== 'action-plan-execution-detail') {
    return null
  }
  const preserved = historySearchWithoutReturnFlag(search)
  if (route.scope?.type === 'cross') {
    return `/cross/history${preserved}`
  }
  if (route.scope?.type === 'establishment') {
    return `/e/${route.scope.establishmentId}/general/history${preserved}`
  }
  return `/general/history${preserved}`
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
  const historyReturn = historyReturnPath(route, search)
  if (historyReturn) {
    return historyReturn
  }

  if (route.kind === 'signal-detail') {
    const analyticsReturn = parseAnalyticsSignalReturnContext(search, { now })
    if (analyticsReturn) {
      return buildAnalyticsPatternDetailPath(analyticsReturn.patternId, analyticsReturn.state)
    }
  }

  if (route.kind === 'signal-action-create') {
    const analyticsReturn = parseAnalyticsSignalReturnContext(search, { now })
    if (analyticsReturn) {
      return buildAnalyticsSignalDetailPath(route.signalId, {
        patternId: analyticsReturn.patternId,
        state: analyticsReturn.state,
      })
    }
  }

  if (route.kind === 'analytics-pattern-detail') {
    return buildAnalyticsReturnPath(parseAnalyticsUrlState(search, { now }))
  }

  if (route.kind === 'action-plan-execution-detail') {
    const hub = getTerrainRouteConfig(route).backPath ?? '/execution'
    const urlOptions =
      route.scope?.type === 'cross' ? { defaultViewMode: 'general' as const } : undefined
    return executionFeedHref(hub, parseExecutionFeedSearch(search, now, urlOptions), urlOptions)
  }

  if (route.kind === 'action-plan-execution-edit') {
    return appendExecutionFeedSearch(
      `/action-plans/executions/${route.executionId}`,
      search,
    )
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

export type TerrainTransitionKind = 'forward' | 'back' | 'fade'

export type TerrainBackResult = 'navigated' | 'root'

type PerformTerrainBackOptions = ResolveTerrainBackPathOptions & {
  activeEstablishmentId?: string | null
}

function canonicalHref(href: string): string {
  return href.split('#')[0] ?? href
}

function sameTerrainScope(left: TerrainScope, right: TerrainScope): boolean {
  if (left.type !== right.type) {
    return false
  }
  if (left.type === 'cross' || right.type === 'cross') {
    return left.type === 'cross' && right.type === 'cross'
  }
  return left.establishmentId === right.establishmentId
}

function isSignalsHub(route: AppRoute): boolean {
  return (
    (route.kind === 'static' && route.path === '/signals') ||
    (route.kind === 'scoped-terrain' && route.page === 'signals')
  )
}

function isExecutionHub(route: AppRoute): boolean {
  return (
    (route.kind === 'static' && route.path === '/execution') ||
    (route.kind === 'scoped-terrain' && route.page === 'execution')
  )
}

function isTechnicalRoute(route: AppRoute): boolean {
  if (
    route.kind === 'invitation' ||
    route.kind === 'email-change' ||
    route.kind === 'password-reset'
  ) {
    return true
  }
  if (route.kind !== 'static') {
    return false
  }
  return (
    route.path === '/' ||
    route.path === '/login' ||
    route.path === '/forgot-password' ||
    route.path === '/onboarding' ||
    route.path === '/pending-onboarding' ||
    route.path === '/select-establishment' ||
    route.path === '/no-establishment'
  )
}

export function sameNavigationDestination(left: AppRoute, right: AppRoute): boolean {
  if (isSignalsHub(left) && isSignalsHub(right)) {
    return true
  }
  if (isExecutionHub(left) && isExecutionHub(right)) {
    return true
  }
  if (left.kind === 'history' && right.kind === 'history') {
    return true
  }
  if (left.kind !== right.kind) {
    return false
  }
  switch (left.kind) {
    case 'static':
      return right.kind === 'static' && left.path === right.path
    case 'scoped-terrain':
      return (
        right.kind === 'scoped-terrain' &&
        left.page === right.page &&
        sameTerrainScope(left.scope, right.scope)
      )
    case 'signal-detail':
      return right.kind === 'signal-detail' && left.signalId === right.signalId
    case 'signal-action-create':
      return right.kind === 'signal-action-create' && left.signalId === right.signalId
    case 'action-plan-execution-detail':
      return (
        right.kind === 'action-plan-execution-detail' && left.executionId === right.executionId
      )
    case 'action-plan-template-detail':
      return (
        right.kind === 'action-plan-template-detail' && left.actionPlanId === right.actionPlanId
      )
    case 'action-plan-template-use':
      return (
        right.kind === 'action-plan-template-use' && left.actionPlanId === right.actionPlanId
      )
    case 'analytics-pattern-detail':
      return right.kind === 'analytics-pattern-detail' && left.patternId === right.patternId
    case 'chat-conversation-detail':
      return (
        right.kind === 'chat-conversation-detail' &&
        left.conversationId === right.conversationId
      )
    case 'action-plan-create':
      return right.kind === 'action-plan-create' && left.origin === right.origin
    case 'action-plan-template-edit':
      return right.kind === 'action-plan-template-edit' && left.actionPlanId === right.actionPlanId
    case 'action-plan-execution-edit':
      return right.kind === 'action-plan-execution-edit' && left.executionId === right.executionId
    case 'team-member-detail':
      return right.kind === 'team-member-detail' && left.membershipId === right.membershipId
    default:
      return false
  }
}

function parentProvenanceIsValid(
  parentHref: string,
  currentRoute: AppRoute,
  activeEstablishmentId: string | null | undefined,
): boolean {
  const parentRoute = parseAppRoute(parentHref)
  if (isTechnicalRoute(parentRoute)) {
    return false
  }
  const parentScope = explicitTerrainScope(parentRoute)
  const currentScope = explicitTerrainScope(currentRoute)
  if (parentScope && currentScope && !sameTerrainScope(parentScope, currentScope)) {
    return false
  }
  if (
    parentScope?.type === 'establishment' &&
    activeEstablishmentId &&
    parentScope.establishmentId !== activeEstablishmentId
  ) {
    return false
  }
  return true
}

export function classifyTerrainTransition(
  from: AppRoute,
  to: AppRoute,
  fromSearch = '',
  toSearch = '',
): TerrainTransitionKind {
  if (getTerrainContentKey(from) === getTerrainContentKey(to)) {
    return 'fade'
  }
  const backOfTo = resolveTerrainBackPath(to, { search: toSearch })
  const backOfFrom = resolveTerrainBackPath(from, { search: fromSearch })
  if (backOfTo && sameNavigationDestination(from, parseAppRoute(backOfTo))) {
    return 'forward'
  }
  if (backOfFrom && sameNavigationDestination(to, parseAppRoute(backOfFrom))) {
    return 'back'
  }
  return 'fade'
}

export function performTerrainBack(
  history: AppHistory,
  options: PerformTerrainBackOptions = {},
): TerrainBackResult {
  if (dismissTopNativeOverlay()) {
    return 'navigated'
  }

  const href = history.getHref()
  const route = parseAppRoute(href)
  const search = options.search ?? getHrefSearch(href)
  const resolved = resolveTerrainBackPath(route, { ...options, search })
  if (!resolved || canonicalHref(resolved) === canonicalHref(href)) {
    return 'root'
  }

  const parentHref = history.getLineage()?.parentHref
  if (
    parentHref &&
    parentProvenanceIsValid(parentHref, route, options.activeEstablishmentId) &&
    sameNavigationDestination(parseAppRoute(parentHref), parseAppRoute(resolved))
  ) {
    if (history.back()) {
      return 'navigated'
    }
  }

  history.navigate(resolved, { intent: 'system' })
  return 'navigated'
}
