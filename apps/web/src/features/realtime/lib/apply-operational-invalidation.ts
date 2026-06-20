import type { QueryClient } from '@tanstack/react-query'

import {
  invalidateActionMutationSurfaces,
  invalidateChecklistExecutionSurfaces,
  invalidateChecklistMutationSurfaces,
  invalidateEstablishmentActionQueries,
  invalidateEstablishmentChecklistQueries,
  invalidateEstablishmentSignalQueries,
} from '@/lib/query-invalidation'

import type { OperationalRealtimeInvalidateEvent } from '../types'

export type ApplyOperationalInvalidationOptions = {
  queryClient: QueryClient
  establishmentId: string
}

export function applyOperationalInvalidation(
  event: OperationalRealtimeInvalidateEvent,
  { queryClient, establishmentId }: ApplyOperationalInvalidationOptions,
) {
  if (event.subject_type === 'signal') {
    invalidateEstablishmentSignalQueries(queryClient, establishmentId)
    return
  }
  if (event.subject_type === 'action') {
    invalidateActionMutationSurfaces(queryClient, establishmentId)
    return
  }
  if (event.subject_type === 'checklist') {
    invalidateChecklistMutationSurfaces(queryClient, establishmentId, event.entity_id)
    return
  }
  if (event.subject_type === 'execution') {
    invalidateChecklistExecutionSurfaces(queryClient, establishmentId, event.entity_id)
  }
}

export function applyOperationalReconnectInvalidation(
  queryClient: QueryClient,
  establishmentId: string,
) {
  invalidateEstablishmentSignalQueries(queryClient, establishmentId)
  invalidateEstablishmentActionQueries(queryClient, establishmentId)
  invalidateEstablishmentChecklistQueries(queryClient, establishmentId)
}
