import type { QueryClient } from '@tanstack/react-query'

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
