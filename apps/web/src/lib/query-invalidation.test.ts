import { describe, expect, it, vi } from 'vitest'

import {
  clearAuthenticatedQueryCache,
  invalidateActionCommentQueries,
  invalidateActionMutationSurfaces,
  invalidateChecklistExecutionSurfaces,
  invalidateEstablishmentActionQueries,
  invalidateEstablishmentChecklistQueries,
  invalidateEstablishmentSignalQueries,
  invalidateSignalCommentQueries,
  purgeNonAuthQueries,
} from '@/lib/query-invalidation'
import { createTestQueryClient } from '@/test-utils'

describe('query-invalidation', () => {
  it('cancels non-auth queries before removing them on purge', () => {
    const queryClient = createTestQueryClient()
    const callOrder: string[] = []
    const cancelSpy = vi.spyOn(queryClient, 'cancelQueries').mockImplementation(() => {
      callOrder.push('cancel')
      return Promise.resolve()
    })
    const removeSpy = vi.spyOn(queryClient, 'removeQueries').mockImplementation(() => {
      callOrder.push('remove')
    })

    purgeNonAuthQueries(queryClient)

    expect(cancelSpy).toHaveBeenCalledOnce()
    expect(removeSpy).toHaveBeenCalledOnce()
    expect(cancelSpy.mock.calls[0]?.[0]).toEqual({ predicate: expect.any(Function) })
    expect(removeSpy.mock.calls[0]?.[0]).toEqual({ predicate: expect.any(Function) })
    expect(callOrder).toEqual(['cancel', 'remove'])
  })

  it('removes unknown query roots by default while preserving auth', () => {
    const queryClient = createTestQueryClient()

    queryClient.setQueryData(['reporting', 'kpi', 'est-a'], { kpi: 1 })
    queryClient.setQueryData(['onboarding', 'sessions', 's-1'], { id: 's-1' })
    queryClient.setQueryData(['signals', 'feed', 'est-a', 'general', {}], { items: ['a'] })
    queryClient.setQueryData(['auth', 'bootstrap'], { authenticated: true })

    purgeNonAuthQueries(queryClient)

    expect(queryClient.getQueryData(['reporting', 'kpi', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['onboarding', 'sessions', 's-1'])).toBeUndefined()
    expect(queryClient.getQueryData(['signals', 'feed', 'est-a', 'general', {}])).toBeUndefined()
    expect(queryClient.getQueryData(['auth', 'bootstrap'])).toEqual({ authenticated: true })
  })

  it('drops cached establishment data across tenants on purge', () => {
    const queryClient = createTestQueryClient()

    queryClient.setQueryData(['signals', 'feed', 'est-a', 'general', {}], { items: ['a'] })
    queryClient.setQueryData(['signals', 'detail', 'est-a', 'sig-1'], { id: 'sig-1' })
    queryClient.setQueryData(['actions', 'execution-feed', 'est-b', 'personal'], { items: [] })
    queryClient.setQueryData(['workspace', 'summary', 'est-a'], { name: 'A' })
    queryClient.setQueryData(['auth', 'bootstrap'], { authenticated: true })

    purgeNonAuthQueries(queryClient)

    expect(queryClient.getQueryData(['signals', 'feed', 'est-a', 'general', {}])).toBeUndefined()
    expect(queryClient.getQueryData(['signals', 'detail', 'est-a', 'sig-1'])).toBeUndefined()
    expect(
      queryClient.getQueryData(['actions', 'execution-feed', 'est-b', 'personal']),
    ).toBeUndefined()
    expect(queryClient.getQueryData(['workspace', 'summary', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['auth', 'bootstrap'])).toEqual({ authenticated: true })
  })

  it('cancels all queries before clear on logout cache reset', () => {
    const queryClient = createTestQueryClient()
    const callOrder: string[] = []
    vi.spyOn(queryClient, 'cancelQueries').mockImplementation(() => {
      callOrder.push('cancel')
      return Promise.resolve()
    })
    vi.spyOn(queryClient, 'clear').mockImplementation(() => {
      callOrder.push('clear')
    })

    clearAuthenticatedQueryCache(queryClient)

    expect(callOrder).toEqual(['cancel', 'clear'])
  })

  it('does not restore cancelled in-flight data after purge', async () => {
    const queryClient = createTestQueryClient()
    let resolveQuery: ((value: { items: string[] }) => void) | undefined

    const fetchPromise = new Promise<{ items: string[] }>((resolve) => {
      resolveQuery = resolve
    })

    const queryKey = ['signals', 'feed', 'est-a', 'general', {}] as const
    const fetchResult = queryClient
      .fetchQuery({
        queryKey,
        queryFn: () => fetchPromise,
      })
      .catch(() => undefined)

    purgeNonAuthQueries(queryClient)
    resolveQuery?.({ items: ['stale-after-switch'] })
    await fetchResult

    expect(queryClient.getQueryData(queryKey)).toBeUndefined()
  })

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

  it('invalidates checklist execution surfaces without global keys', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    invalidateChecklistExecutionSurfaces(queryClient, 'est-1', 'exec-1')

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['checklists', 'execution-detail', 'est-1', 'exec-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['checklists', 'templates', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['actions', 'execution-feed', 'est-1'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['checklists'] })
  })

  it('invalidates signal comment queries without global keys', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    invalidateSignalCommentQueries(queryClient, 'est-1', 'sig-1')

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['comments', 'signal', 'est-1', 'sig-1'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['comments'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['comments', 'signal', 'est-1'] })
  })

  it('invalidates action comment queries without global keys', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    invalidateActionCommentQueries(queryClient, 'est-1', 'act-1')

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['comments', 'action', 'est-1', 'act-1'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['comments'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['comments', 'action', 'est-1'] })
  })
})
