import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { analyticsQueryKeys } from '@/features/analytics/api'
import {
  applyOperationalInvalidation,
  applyOperationalReconnectInvalidation,
} from '@/features/realtime/lib/apply-operational-invalidation'
import type { OperationalRealtimeInvalidateEvent } from '@/features/realtime/types'
import { DASHBOARD_REALTIME_INVALIDATION_MS } from '@/lib/query-invalidation'
import { queryClient } from '@/lib/query-client'
import { createTestQueryClient } from '@/test-utils'

function signalEvent(reason: string, establishmentId = 'est-1'): OperationalRealtimeInvalidateEvent {
  return {
    type: 'invalidate',
    subject_type: 'signal',
    reason,
    establishment_id: establishmentId,
    entity_id: 'sig-1',
    occurred_at: '2026-06-19T12:00:00Z',
  }
}

describe('applyOperationalInvalidation', () => {
  it('invalidates signal queries for signal subject_type', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'signal',
      reason: 'signal.updated',
      establishment_id: 'est-1',
      entity_id: 'sig-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ['action-plans', 'action-plan-execution-feed', 'est-1'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ predicate: expect.any(Function) })
    invalidateSpy.mockRestore()
  })

  it('invalidates action plan catalog queries for action_plan.updated', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'action_plan',
      reason: 'action_plan.updated',
      establishment_id: 'est-1',
      entity_id: 'plan-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['action-plans', 'catalog', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['action-plans', 'detail', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'detail', 'est-1', 'plan-1'],
    })
    invalidateSpy.mockRestore()
  })

  it.each([
    'action_plan_execution.created',
    'action_plan_execution.updated',
    'action_plan_execution.canceled',
    'action_plan_execution.done',
    'action_plan_execution.pending_validation',
  ] as const)('invalidates action plan execution feed for %s', (reason) => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'action_plan_execution',
      reason,
      establishment_id: 'est-1',
      entity_id: 'ap-exec-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'action-plan-execution-feed', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'execution-detail', 'est-1', 'ap-exec-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    invalidateSpy.mockRestore()
  })

  it('invalidates broad execution detail for action_plan_assignee without feed', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'action_plan_assignee',
      reason: 'action_plan_assignee.updated',
      establishment_id: 'est-1',
      entity_id: 'assignee-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'execution-detail', 'est-1'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ['action-plans', 'action-plan-execution-feed', 'est-1'],
    })
    invalidateSpy.mockRestore()
  })

  it.each([
    ['comment.signal.created', ['comments', 'signal', 'est-1', 'sig-1'], false],
    ['comment.signal.inherited', ['comments', 'action-plan-execution', 'est-1', 'exec-1'], false],
    ['comment.execution.created', ['comments', 'action-plan-execution', 'est-1', 'exec-1'], true],
    ['comment.execution.resolved', ['comments', 'action-plan-execution', 'est-1', 'exec-1'], true],
    ['comment.execution.unresolved', ['comments', 'action-plan-execution', 'est-1', 'exec-1'], true],
  ] as const)('invalidates comment queries for %s', (reason, queryKey, invalidatesExecutionFeed) => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const entityId = reason === 'comment.signal.created' ? 'sig-1' : 'exec-1'
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'comment',
      reason,
      establishment_id: 'est-1',
      entity_id: entityId,
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: [...queryKey] })
    if (invalidatesExecutionFeed) {
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['action-plans', 'action-plan-execution-feed', 'est-1'],
      })
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['action-plans', 'action-plan-execution-calendar', 'est-1'],
      })
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['action-plans', 'cross-action-plan-execution-feed'],
      })
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['action-plans', 'cross-action-plan-execution-calendar'],
      })
      expect(invalidateSpy).toHaveBeenCalledTimes(5)
    } else {
      expect(invalidateSpy).toHaveBeenCalledOnce()
    }
    invalidateSpy.mockRestore()
  })

  it('ignores unknown comment reason', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'comment',
      reason: 'comment.unknown',
      establishment_id: 'est-1',
      entity_id: 'sig-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).not.toHaveBeenCalled()
    invalidateSpy.mockRestore()
  })

  it.each([
    'notification.created',
    'notification.updated',
    'notification.bulk_updated',
  ] as const)('invalidates notification list queries for %s', (reason) => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'notification',
      reason,
      establishment_id: 'est-1',
      entity_id: 'notif-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['notifications', 'list', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledOnce()
    invalidateSpy.mockRestore()
  })

  it('ignores unknown notification reason', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'notification',
      reason: 'notification.unknown',
      establishment_id: 'est-1',
      entity_id: 'notif-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).not.toHaveBeenCalled()
    invalidateSpy.mockRestore()
  })
})

describe('applyOperationalReconnectInvalidation', () => {
  it('invalidates signal, action plan, and notification queries', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    applyOperationalReconnectInvalidation(queryClient, 'est-1')

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['action-plans', 'catalog', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['action-plans', 'detail', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'action-plan-execution-feed', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['notifications', 'list', 'est-1'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ predicate: expect.any(Function) })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['analytics', 'dashboard'] })
    invalidateSpy.mockRestore()
  })

  it('does not invalidate dashboard queries', () => {
    const client = createTestQueryClient()
    const dashboardKey = analyticsQueryKeys.dashboard({
      periodDays: 7,
      establishmentId: 'est-1',
    })
    client.setQueryData(dashboardKey, { total: 1 })

    applyOperationalReconnectInvalidation(client, 'est-1')

    expect(client.getQueryState(dashboardKey)?.isInvalidated).toBe(false)
  })
})

describe('signal created dashboard invalidation', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.advanceTimersByTime(DASHBOARD_REALTIME_INVALIDATION_MS)
    vi.useRealTimers()
  })

  it('invalidates dashboard and rankings for the WS establishment only on signal.created', () => {
    const client = createTestQueryClient()
    const dashboardEst1 = analyticsQueryKeys.dashboard({
      periodDays: 7,
      establishmentId: 'est-1',
    })
    const rankingsEst1 = analyticsQueryKeys.dashboardRankings({
      periodDays: 7,
      establishmentId: 'est-1',
      kind: 'recurring',
    })
    const dashboardEst2 = analyticsQueryKeys.dashboard({
      periodDays: 7,
      establishmentId: 'est-2',
    })
    client.setQueryData(dashboardEst1, { total: 1 })
    client.setQueryData(rankingsEst1, { items: [] })
    client.setQueryData(dashboardEst2, { total: 2 })

    applyOperationalInvalidation(signalEvent('signal.created'), {
      queryClient: client,
      establishmentId: 'est-1',
    })
    applyOperationalInvalidation(
      { ...signalEvent('signal.created'), entity_id: 'sig-2' },
      { queryClient: client, establishmentId: 'est-1' },
    )

    expect(client.getQueryState(dashboardEst1)?.isInvalidated).toBe(false)
    vi.advanceTimersByTime(DASHBOARD_REALTIME_INVALIDATION_MS)
    expect(client.getQueryState(dashboardEst1)?.isInvalidated).toBe(true)
    expect(client.getQueryState(rankingsEst1)?.isInvalidated).toBe(true)
    expect(client.getQueryState(dashboardEst2)?.isInvalidated).toBe(false)
  })

  it('does not invalidate dashboard on signal.updated', () => {
    const client = createTestQueryClient()
    const dashboardEst1 = analyticsQueryKeys.dashboard({
      periodDays: 7,
      establishmentId: 'est-1',
    })
    client.setQueryData(dashboardEst1, { total: 1 })

    applyOperationalInvalidation(signalEvent('signal.updated'), {
      queryClient: client,
      establishmentId: 'est-1',
    })
    vi.advanceTimersByTime(DASHBOARD_REALTIME_INVALIDATION_MS)

    expect(client.getQueryState(dashboardEst1)?.isInvalidated).toBe(false)
  })

  it('refetches dashboard once for a close signal.created burst', () => {
    const client = createTestQueryClient()
    const dashboardKey = analyticsQueryKeys.dashboard({
      periodDays: 7,
      establishmentId: 'est-1',
    })
    client.setQueryData(dashboardKey, { total: 1 })
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    applyOperationalInvalidation(signalEvent('signal.created', 'est-1'), {
      queryClient: client,
      establishmentId: 'est-1',
    })
    applyOperationalInvalidation(
      {
        ...signalEvent('signal.created', 'est-1'),
        entity_id: 'sig-2',
      },
      { queryClient: client, establishmentId: 'est-1' },
    )
    applyOperationalInvalidation(
      {
        ...signalEvent('signal.created', 'est-1'),
        entity_id: 'sig-3',
      },
      { queryClient: client, establishmentId: 'est-1' },
    )

    const dashboardCallsBeforeTimer = invalidateSpy.mock.calls.filter((call) =>
      'predicate' in (call[0] ?? {}),
    )
    expect(dashboardCallsBeforeTimer).toHaveLength(0)
    vi.advanceTimersByTime(DASHBOARD_REALTIME_INVALIDATION_MS)
    const dashboardCalls = invalidateSpy.mock.calls.filter((call) =>
      'predicate' in (call[0] ?? {}),
    )
    expect(dashboardCalls).toHaveLength(1)
    expect(client.getQueryState(dashboardKey)?.isInvalidated).toBe(true)
  })
})
