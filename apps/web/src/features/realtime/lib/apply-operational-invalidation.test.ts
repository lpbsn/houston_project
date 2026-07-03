import { describe, expect, it, vi } from 'vitest'

import { queryClient } from '@/lib/query-client'
import { applyOperationalInvalidation, applyOperationalReconnectInvalidation } from '@/features/realtime/lib/apply-operational-invalidation'
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
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['actions', 'execution-feed', 'est-1'] })
    invalidateSpy.mockRestore()
  })

  it('invalidates action and signal queries for action.created', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'action',
      reason: 'action.created',
      establishment_id: 'est-1',
      entity_id: 'act-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'execution-feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'detail', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    invalidateSpy.mockRestore()
  })

  it('invalidates action and signal queries for action.updated', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'action',
      reason: 'action.updated',
      establishment_id: 'est-1',
      entity_id: 'act-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'execution-feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'detail', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    invalidateSpy.mockRestore()
  })

  it('invalidates checklist mutation surfaces for checklist.updated', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'checklist',
      reason: 'checklist.updated',
      establishment_id: 'est-1',
      entity_id: 'tpl-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['checklists', 'templates', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['checklists', 'template-detail', 'est-1', 'tpl-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'execution-feed', 'est-1'] })
    invalidateSpy.mockRestore()
  })

  it.each(['execution.created', 'execution.updated'] as const)(
    'invalidates execution surfaces for %s',
    (reason) => {
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
      const event: OperationalRealtimeInvalidateEvent = {
        type: 'invalidate',
        subject_type: 'execution',
        reason,
        establishment_id: 'est-1',
        entity_id: 'exec-1',
        occurred_at: '2026-06-19T12:00:00Z',
      }

      applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['checklists', 'execution-detail', 'est-1', 'exec-1'],
      })
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['checklists', 'templates', 'est-1'] })
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'execution-feed', 'est-1'] })
      invalidateSpy.mockRestore()
    },
  )

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
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ['actions', 'execution-feed', 'est-1'],
    })
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
    [
      'comment.signal.inherited',
      [
        ['comments', 'action', 'est-1', 'act-1'],
        ['comments', 'action-plan-execution', 'est-1', 'act-1'],
      ],
    ],
    ['comment.action.created', ['comments', 'action', 'est-1', 'act-1']],
    ['comment.action.resolved', ['comments', 'action', 'est-1', 'act-1']],
    ['comment.action.unresolved', ['comments', 'action', 'est-1', 'act-1']],
    ['comment.execution.created', ['comments', 'action-plan-execution', 'est-1', 'exec-1']],
    ['comment.execution.resolved', ['comments', 'action-plan-execution', 'est-1', 'exec-1']],
    ['comment.execution.unresolved', ['comments', 'action-plan-execution', 'est-1', 'exec-1']],
  ] as const)('invalidates comment queries for %s', (reason, queryKey) => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const entityId =
      reason === 'comment.signal.created'
        ? 'sig-1'
        : reason.startsWith('comment.execution.')
          ? 'exec-1'
          : 'act-1'
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'comment',
      reason,
      establishment_id: 'est-1',
      entity_id: entityId,
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    const expectedKeys = Array.isArray(queryKey[0]) ? queryKey : [queryKey]
    for (const key of expectedKeys) {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: key })
    }
    expect(invalidateSpy).toHaveBeenCalledTimes(expectedKeys.length)
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
  it('invalidates signal, action, checklist, and notification queries', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    applyOperationalReconnectInvalidation(queryClient, 'est-1')

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'execution-feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'detail', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['checklists', 'templates', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['checklists', 'template-detail', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['notifications', 'list', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'action-plan-execution-feed', 'est-1'],
    })
    invalidateSpy.mockRestore()
  })
})
