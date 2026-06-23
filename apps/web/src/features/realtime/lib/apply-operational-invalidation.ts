import type { QueryClient } from '@tanstack/react-query'

import {
  invalidateActionCommentQueries,
  invalidateActionMutationSurfaces,
  invalidateChecklistExecutionSurfaces,
  invalidateChecklistMutationSurfaces,
  invalidateEstablishmentActionQueries,
  invalidateEstablishmentChecklistQueries,
  invalidateEstablishmentNotificationQueries,
  invalidateEstablishmentSignalQueries,
  invalidateSignalCommentQueries,
} from '@/lib/query-invalidation'

import type { OperationalRealtimeInvalidateEvent } from '../types'

const NOTIFICATION_INVALIDATION_REASONS = new Set([
  'notification.created',
  'notification.updated',
  'notification.bulk_updated',
])

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
    return
  }
  if (event.subject_type === 'comment') {
    switch (event.reason) {
      case 'comment.signal.created':
        invalidateSignalCommentQueries(queryClient, establishmentId, event.entity_id)
        break
      case 'comment.signal.inherited':
      case 'comment.action.created':
      case 'comment.action.resolved':
      case 'comment.action.unresolved':
        invalidateActionCommentQueries(queryClient, establishmentId, event.entity_id)
        break
      default:
        break
    }
    return
  }
  if (event.subject_type === 'notification') {
    if (!NOTIFICATION_INVALIDATION_REASONS.has(event.reason)) {
      return
    }
    invalidateEstablishmentNotificationQueries(queryClient, establishmentId)
  }
}

export function applyOperationalReconnectInvalidation(
  queryClient: QueryClient,
  establishmentId: string,
) {
  invalidateEstablishmentSignalQueries(queryClient, establishmentId)
  invalidateEstablishmentActionQueries(queryClient, establishmentId)
  invalidateEstablishmentChecklistQueries(queryClient, establishmentId)
  invalidateEstablishmentNotificationQueries(queryClient, establishmentId)
}
