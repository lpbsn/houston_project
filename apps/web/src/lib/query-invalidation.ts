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
