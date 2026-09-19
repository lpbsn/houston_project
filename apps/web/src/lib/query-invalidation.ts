import type { Query, QueryClient } from '@tanstack/react-query'

export function isAuthQueryKey(queryKey: readonly unknown[]): boolean {
  return queryKey[0] === 'auth'
}

function isNonAuthQuery(query: Query): boolean {
  return !isAuthQueryKey(query.queryKey)
}

/** Establishment switch: cancel then remove every query except auth. */
export function purgeNonAuthQueries(queryClient: QueryClient) {
  void queryClient.cancelQueries({ predicate: isNonAuthQuery })
  queryClient.removeQueries({ predicate: isNonAuthQuery })
}

/** Logout / invalidated session: cancel in-flight work then wipe the cache. */
export function clearAuthenticatedQueryCache(queryClient: QueryClient) {
  void queryClient.cancelQueries()
  queryClient.clear()
}

export function invalidateEstablishmentSignalQueries(
  queryClient: QueryClient,
  establishmentId: string,
) {
  void queryClient.invalidateQueries({ queryKey: ['signals', 'feed', establishmentId] })
  void queryClient.invalidateQueries({ queryKey: ['signals', 'detail', establishmentId] })
}

function isEstablishmentDashboardQueryKey(
  queryKey: readonly unknown[],
  establishmentId: string,
): boolean {
  const [root, kind, params] = queryKey
  if (root !== 'analytics') {
    return false
  }
  if (kind !== 'dashboard' && kind !== 'dashboard-rankings') {
    return false
  }
  if (params === null || typeof params !== 'object' || Array.isArray(params)) {
    return false
  }
  return (params as { establishmentId?: unknown }).establishmentId === establishmentId
}

export function invalidateEstablishmentDashboardQueries(
  queryClient: QueryClient,
  establishmentId: string,
) {
  void queryClient.invalidateQueries({
    predicate: (query) => isEstablishmentDashboardQueryKey(query.queryKey, establishmentId),
  })
}

/** Trailing window for realtime `signal.created` bursts (not used after qualify). */
export const DASHBOARD_REALTIME_INVALIDATION_MS = 50

const pendingRealtimeDashboardInvalidations = new WeakMap<
  QueryClient,
  Map<string, ReturnType<typeof setTimeout>>
>()

export function scheduleEstablishmentDashboardInvalidation(
  queryClient: QueryClient,
  establishmentId: string,
) {
  let byEstablishment = pendingRealtimeDashboardInvalidations.get(queryClient)
  if (!byEstablishment) {
    byEstablishment = new Map()
    pendingRealtimeDashboardInvalidations.set(queryClient, byEstablishment)
  }
  const existing = byEstablishment.get(establishmentId)
  if (existing !== undefined) {
    clearTimeout(existing)
  }
  const timer = setTimeout(() => {
    byEstablishment.delete(establishmentId)
    invalidateEstablishmentDashboardQueries(queryClient, establishmentId)
  }, DASHBOARD_REALTIME_INVALIDATION_MS)
  byEstablishment.set(establishmentId, timer)
}

export function invalidateSignalCommentQueries(
  queryClient: QueryClient,
  establishmentId: string,
  signalId: string,
) {
  void queryClient.invalidateQueries({
    queryKey: ['comments', 'signal', establishmentId, signalId],
  })
}

export function invalidateExecutionCommentQueries(
  queryClient: QueryClient,
  establishmentId: string,
  executionId: string,
) {
  void queryClient.invalidateQueries({
    queryKey: ['comments', 'action-plan-execution', establishmentId, executionId],
  })
}

export function invalidateEstablishmentNotificationQueries(
  queryClient: QueryClient,
  establishmentId: string,
) {
  void queryClient.invalidateQueries({ queryKey: ['notifications', 'list', establishmentId] })
}

export function invalidateEstablishmentActionPlanCatalogQueries(
  queryClient: QueryClient,
  establishmentId: string,
) {
  void queryClient.invalidateQueries({ queryKey: ['action-plans', 'catalog', establishmentId] })
  void queryClient.invalidateQueries({ queryKey: ['action-plans', 'detail', establishmentId] })
}

export function invalidateActionPlanExecutionFeedQueries(
  queryClient: QueryClient,
  establishmentId: string,
) {
  void queryClient.invalidateQueries({
    queryKey: ['action-plans', 'action-plan-execution-feed', establishmentId],
  })
  void queryClient.invalidateQueries({
    queryKey: ['action-plans', 'action-plan-execution-calendar', establishmentId],
  })
  void queryClient.invalidateQueries({
    queryKey: ['action-plans', 'cross-action-plan-execution-feed'],
  })
  void queryClient.invalidateQueries({
    queryKey: ['action-plans', 'cross-action-plan-execution-calendar'],
  })
}

export function invalidateActionPlanExecutionUpcomingQueries(
  queryClient: QueryClient,
  establishmentId: string,
) {
  void queryClient.invalidateQueries({
    queryKey: ['action-plans', 'action-plan-execution-upcoming', establishmentId],
  })
}

export function invalidateActionPlanExecutionDetailQueries(
  queryClient: QueryClient,
  establishmentId: string,
  executionId?: string,
) {
  if (executionId) {
    void queryClient.invalidateQueries({
      queryKey: ['action-plans', 'execution-detail', establishmentId, executionId],
    })
    return
  }
  void queryClient.invalidateQueries({
    queryKey: ['action-plans', 'execution-detail', establishmentId],
  })
}

export function invalidateActionPlanExecutionSurfaces(
  queryClient: QueryClient,
  establishmentId: string,
  executionId?: string,
) {
  invalidateActionPlanExecutionFeedQueries(queryClient, establishmentId)
  invalidateActionPlanExecutionUpcomingQueries(queryClient, establishmentId)
  invalidateActionPlanExecutionDetailQueries(queryClient, establishmentId, executionId)
  invalidateEstablishmentSignalQueries(queryClient, establishmentId)
}

export function invalidateActionPlanAssigneeSurfaces(
  queryClient: QueryClient,
  establishmentId: string,
) {
  invalidateActionPlanExecutionDetailQueries(queryClient, establishmentId)
}

export function invalidateActionPlanMutationSurfaces(
  queryClient: QueryClient,
  establishmentId: string,
  actionPlanId?: string,
) {
  invalidateEstablishmentActionPlanCatalogQueries(queryClient, establishmentId)
  if (actionPlanId) {
    void queryClient.invalidateQueries({
      queryKey: ['action-plans', 'detail', establishmentId, actionPlanId],
    })
  }
}
