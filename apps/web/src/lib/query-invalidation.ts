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

export function invalidateEstablishmentActionQueries(
  queryClient: QueryClient,
  establishmentId: string,
) {
  void queryClient.invalidateQueries({ queryKey: ['actions', 'execution-feed', establishmentId] })
  void queryClient.invalidateQueries({ queryKey: ['actions', 'detail', establishmentId] })
}

export function invalidateEstablishmentChecklistQueries(
  queryClient: QueryClient,
  establishmentId: string,
) {
  void queryClient.invalidateQueries({ queryKey: ['checklists', 'templates', establishmentId] })
  void queryClient.invalidateQueries({ queryKey: ['checklists', 'template-detail', establishmentId] })
  void queryClient.invalidateQueries({ queryKey: ['checklists', 'assignments', establishmentId] })
  void queryClient.invalidateQueries({
    queryKey: ['checklists', 'execution-detail', establishmentId],
  })
}

export function invalidateActionMutationSurfaces(
  queryClient: QueryClient,
  establishmentId: string,
) {
  invalidateEstablishmentActionQueries(queryClient, establishmentId)
  invalidateEstablishmentSignalQueries(queryClient, establishmentId)
}

export function invalidateChecklistMutationSurfaces(
  queryClient: QueryClient,
  establishmentId: string,
  templateId?: string,
) {
  invalidateEstablishmentChecklistQueries(queryClient, establishmentId)
  if (templateId) {
    void queryClient.invalidateQueries({
      queryKey: ['checklists', 'template-detail', establishmentId, templateId],
    })
  }
  invalidateEstablishmentActionQueries(queryClient, establishmentId)
}

export function invalidateChecklistExecutionSurfaces(
  queryClient: QueryClient,
  establishmentId: string,
  executionId: string,
) {
  void queryClient.invalidateQueries({
    queryKey: ['checklists', 'execution-detail', establishmentId, executionId],
  })
  invalidateChecklistMutationSurfaces(queryClient, establishmentId)
}
