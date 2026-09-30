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

import { removeHydratedFeedEntity } from '@/lib/feed-external-updates'

import { observationsQueryKeys } from '@/features/observations/api'
import { isObservationProcessingTracked } from '@/features/observations/lib/observation-processing-tracker-store'

import type { OperationalRealtimeInvalidateEvent } from '../types'

const TERMINAL_EXECUTION_REASONS = new Set([
  'action_plan_execution.done',
  'action_plan_execution.canceled',
])

const TERMINAL_SIGNAL_REASONS = new Set(['signal.resolved', 'signal.canceled'])

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
    if (TERMINAL_SIGNAL_REASONS.has(event.reason)) {
      removeHydratedFeedEntity(['signals', 'feed', establishmentId], event.entity_id)
      removeHydratedFeedEntity(['signals', 'cross-feed'], event.entity_id)
    }
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
    if (TERMINAL_EXECUTION_REASONS.has(event.reason)) {
      removeHydratedFeedEntity(
        ['action-plans', 'action-plan-execution-feed', establishmentId],
        event.entity_id,
      )
      removeHydratedFeedEntity(
        ['action-plans', 'cross-action-plan-execution-feed'],
        event.entity_id,
      )
      removeHydratedFeedEntity(
        ['action-plans', 'cross-action-plan-execution-feed-pins'],
        event.entity_id,
      )
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
