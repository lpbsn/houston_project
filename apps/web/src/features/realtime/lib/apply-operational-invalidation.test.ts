import { describe, expect, it, vi } from 'vitest'

import { queryClient } from '@/lib/query-client'
import {
  applyOperationalInvalidation,
  applyOperationalReconnectInvalidation,
} from '@/features/realtime/lib/apply-operational-invalidation'
import type { OperationalRealtimeInvalidateEvent } from '@/features/realtime/types'

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
    ['comment.signal.created', ['comments', 'signal', 'est-1', 'sig-1']],
    ['comment.signal.inherited', ['comments', 'action-plan-execution', 'est-1', 'exec-1']],
    ['comment.execution.created', ['comments', 'action-plan-execution', 'est-1', 'exec-1']],
    ['comment.execution.resolved', ['comments', 'action-plan-execution', 'est-1', 'exec-1']],
    ['comment.execution.unresolved', ['comments', 'action-plan-execution', 'est-1', 'exec-1']],
  ] as const)('invalidates comment queries for %s', (reason, queryKey) => {
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
    expect(invalidateSpy).toHaveBeenCalledOnce()
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
    invalidateSpy.mockRestore()
  })
})
