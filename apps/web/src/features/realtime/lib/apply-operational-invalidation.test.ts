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

  it('ignores comment subject_type until PR4', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const event: OperationalRealtimeInvalidateEvent = {
      type: 'invalidate',
      subject_type: 'comment',
      reason: 'comment.signal.created',
      establishment_id: 'est-1',
      entity_id: 'sig-1',
      occurred_at: '2026-06-19T12:00:00Z',
    }

    applyOperationalInvalidation(event, { queryClient, establishmentId: 'est-1' })

    expect(invalidateSpy).not.toHaveBeenCalled()
    invalidateSpy.mockRestore()
  })
})

describe('applyOperationalReconnectInvalidation', () => {
  it('invalidates signal, action, and checklist queries', () => {
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
    invalidateSpy.mockRestore()
  })
})
