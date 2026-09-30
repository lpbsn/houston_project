import type { QueryClient } from '@tanstack/react-query'

import {
  invalidateActionPlanAssigneeSurfaces,
  invalidateActionPlanExecutionFeedQueries,
  invalidateActionPlanExecutionSurfaces,
  invalidateActionPlanExecutionUpcomingQueries,
  invalidateActionPlanMutationSurfaces,
  invalidateEstablishmentActionPlanCatalogQueries,
  invalidateEstablishmentNotificationQueries,
  invalidateEstablishmentSignalQueries,
  invalidateExecutionCommentQueries,
  invalidateSignalCommentQueries,
  scheduleEstablishmentDashboardInvalidation,
} from '@/lib/query-invalidation'

import { retainTerminalExecutionInFeedCaches } from '@/features/action-plans/lib/action-plan-execution-feed-cache'
import { observationsQueryKeys } from '@/features/observations/api'
import { isObservationProcessingTracked } from '@/features/observations/lib/observation-processing-tracker-store'

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
    if (event.reason === 'signal.created') {
      scheduleEstablishmentDashboardInvalidation(queryClient, establishmentId)
    }
    return
  }
  if (event.subject_type === 'action_plan') {
    invalidateActionPlanMutationSurfaces(queryClient, establishmentId, event.entity_id)
    return
  }
  if (event.subject_type === 'action_plan_execution') {
    if (
      event.reason === 'action_plan_execution.done' ||
      event.reason === 'action_plan_execution.canceled'
    ) {
      retainTerminalExecutionInFeedCaches(queryClient, {
        establishmentId,
        executionId: event.entity_id,
        status: event.reason === 'action_plan_execution.done' ? 'done' : 'canceled',
        occurredAt: event.occurred_at,
      })
    }
    invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, event.entity_id)
    return
  }
  if (event.subject_type === 'action_plan_execution_task') {
    invalidateActionPlanExecutionSurfaces(queryClient, establishmentId)
    return
  }
  if (event.subject_type === 'action_plan_assignee') {
    invalidateActionPlanAssigneeSurfaces(queryClient, establishmentId)
    return
  }
  if (event.subject_type === 'comment') {
    switch (event.reason) {
      case 'comment.signal.created':
        invalidateSignalCommentQueries(queryClient, establishmentId, event.entity_id)
        break
      case 'comment.signal.inherited':
        invalidateExecutionCommentQueries(queryClient, establishmentId, event.entity_id)
        break
      case 'comment.execution.created':
      case 'comment.execution.resolved':
      case 'comment.execution.unresolved':
        invalidateExecutionCommentQueries(queryClient, establishmentId, event.entity_id)
        invalidateActionPlanExecutionFeedQueries(queryClient, establishmentId)
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
    return
  }
  if (event.subject_type === 'observation_processing') {
    if (event.reason !== 'observation_processing.updated') {
      return
    }
    if (!isObservationProcessingTracked(event.entity_id, establishmentId)) {
      return
    }
    void queryClient.invalidateQueries({
      queryKey: observationsQueryKeys.processingStatus(establishmentId, event.entity_id),
    })
  }
}

export function applyOperationalReconnectInvalidation(
  queryClient: QueryClient,
  establishmentId: string,
) {
  const force = { force: true } as const
  invalidateEstablishmentSignalQueries(queryClient, establishmentId, force)
  invalidateEstablishmentActionPlanCatalogQueries(queryClient, establishmentId)
  invalidateActionPlanExecutionFeedQueries(queryClient, establishmentId, force)
  invalidateActionPlanExecutionUpcomingQueries(queryClient, establishmentId)
  void queryClient.invalidateQueries({
    queryKey: ['action-plans', 'cross-action-plan-execution-upcoming'],
  })
  invalidateEstablishmentNotificationQueries(queryClient, establishmentId)
}
