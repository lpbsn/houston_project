import { describe, expect, it, vi } from 'vitest'

import {
  invalidateActionMutationSurfaces,
  invalidateEstablishmentActionQueries,
  invalidateEstablishmentChecklistQueries,
  invalidateEstablishmentSignalQueries,
} from '@/lib/query-invalidation'
import { createTestQueryClient } from '@/test-utils'

describe('query-invalidation', () => {
  it('invalidates establishment-scoped signal queries', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    invalidateEstablishmentSignalQueries(queryClient, 'est-1')

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['signals'] })
  })

  it('invalidates establishment-scoped action queries', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    invalidateEstablishmentActionQueries(queryClient, 'est-1')

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['actions', 'execution-feed', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'detail', 'est-1'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['actions'] })
  })

  it('invalidates establishment-scoped checklist queries', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    invalidateEstablishmentChecklistQueries(queryClient, 'est-1')

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['checklists', 'templates', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['checklists', 'template-detail', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['checklists', 'assignments', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['checklists', 'execution-detail', 'est-1'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['checklists'] })
  })

  it('invalidates action mutation surfaces without global keys', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    invalidateActionMutationSurfaces(queryClient, 'est-1')

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['actions', 'execution-feed', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['actions'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['signals'] })
  })
})
