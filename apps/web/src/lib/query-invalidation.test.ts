import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { analyticsQueryKeys } from '@/features/analytics/api'
import {
  DASHBOARD_REALTIME_INVALIDATION_MS,
  clearAuthenticatedQueryCache,
  invalidateEstablishmentDashboardQueries,
  invalidateEstablishmentSignalQueries,
  invalidateExecutionCommentQueries,
  invalidateSignalCommentQueries,
  purgeNonAuthQueries,
  scheduleEstablishmentDashboardInvalidation,
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
    queryClient.setQueryData(
      ['action-plans', 'action-plan-execution-feed', 'est-b', 'personal'],
      { items: [] },
    )
    queryClient.setQueryData(['workspace', 'summary', 'est-a'], { name: 'A' })
    queryClient.setQueryData(['auth', 'bootstrap'], { authenticated: true })

    purgeNonAuthQueries(queryClient)

    expect(queryClient.getQueryData(['signals', 'feed', 'est-a', 'general', {}])).toBeUndefined()
    expect(queryClient.getQueryData(['signals', 'detail', 'est-a', 'sig-1'])).toBeUndefined()
    expect(
      queryClient.getQueryData(['action-plans', 'action-plan-execution-feed', 'est-b', 'personal']),
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

  it('invalidates only dashboard and rankings for the given establishment', () => {
    const queryClient = createTestQueryClient()
    const dashboardA = analyticsQueryKeys.dashboard({
      periodDays: 7,
      establishmentId: 'est-a',
    })
    const rankingsA = analyticsQueryKeys.dashboardRankings({
      periodDays: 7,
      establishmentId: 'est-a',
      kind: 'recurring',
    })
    const dashboardB = analyticsQueryKeys.dashboard({
      periodDays: 7,
      establishmentId: 'est-b',
    })
    const rankingsB = analyticsQueryKeys.dashboardRankings({
      periodDays: 30,
      establishmentId: 'est-b',
      kind: 'locations',
    })
    const patternsA = ['analytics', 'patterns', { establishmentId: 'est-a' }] as const

    queryClient.setQueryData(dashboardA, { total: 1 })
    queryClient.setQueryData(rankingsA, { items: [] })
    queryClient.setQueryData(dashboardB, { total: 2 })
    queryClient.setQueryData(rankingsB, { items: ['b'] })
    queryClient.setQueryData(patternsA, { items: ['pattern'] })

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    invalidateEstablishmentDashboardQueries(queryClient, 'est-a')

    expect(invalidateSpy).toHaveBeenCalledOnce()
    expect(invalidateSpy.mock.calls[0]?.[0]).toEqual({ predicate: expect.any(Function) })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['analytics'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['analytics', 'dashboard'] })
    expect(queryClient.getQueryState(dashboardA)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(rankingsA)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(dashboardB)?.isInvalidated).toBe(false)
    expect(queryClient.getQueryState(rankingsB)?.isInvalidated).toBe(false)
    expect(queryClient.getQueryState(patternsA)?.isInvalidated).toBe(false)
    expect(queryClient.getQueryData(dashboardB)).toEqual({ total: 2 })
    expect(queryClient.getQueryData(patternsA)).toEqual({ items: ['pattern'] })
  })

  describe('scheduleEstablishmentDashboardInvalidation', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.advanceTimersByTime(DASHBOARD_REALTIME_INVALIDATION_MS)
      vi.useRealTimers()
    })

    it('coalesces close schedules for one establishment into a single invalidation', () => {
      const queryClient = createTestQueryClient()
      const dashboardA = analyticsQueryKeys.dashboard({
        periodDays: 7,
        establishmentId: 'est-a',
      })
      queryClient.setQueryData(dashboardA, { total: 1 })
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      scheduleEstablishmentDashboardInvalidation(queryClient, 'est-a')
      scheduleEstablishmentDashboardInvalidation(queryClient, 'est-a')
      scheduleEstablishmentDashboardInvalidation(queryClient, 'est-a')

      expect(invalidateSpy).not.toHaveBeenCalled()
      vi.advanceTimersByTime(DASHBOARD_REALTIME_INVALIDATION_MS - 1)
      expect(invalidateSpy).not.toHaveBeenCalled()
      vi.advanceTimersByTime(1)
      expect(invalidateSpy).toHaveBeenCalledOnce()
      expect(queryClient.getQueryState(dashboardA)?.isInvalidated).toBe(true)
    })

    it('keeps establishment schedules isolated', () => {
      const queryClient = createTestQueryClient()
      const dashboardA = analyticsQueryKeys.dashboard({
        periodDays: 7,
        establishmentId: 'est-a',
      })
      const dashboardB = analyticsQueryKeys.dashboard({
        periodDays: 7,
        establishmentId: 'est-b',
      })
      queryClient.setQueryData(dashboardA, { total: 1 })
      queryClient.setQueryData(dashboardB, { total: 2 })
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      scheduleEstablishmentDashboardInvalidation(queryClient, 'est-a')
      scheduleEstablishmentDashboardInvalidation(queryClient, 'est-b')
      scheduleEstablishmentDashboardInvalidation(queryClient, 'est-a')

      vi.advanceTimersByTime(DASHBOARD_REALTIME_INVALIDATION_MS)

      expect(invalidateSpy).toHaveBeenCalledTimes(2)
      expect(queryClient.getQueryState(dashboardA)?.isInvalidated).toBe(true)
      expect(queryClient.getQueryState(dashboardB)?.isInvalidated).toBe(true)
    })

    it('runs a second invalidation after the window for spaced schedules', () => {
      const queryClient = createTestQueryClient()
      const dashboardA = analyticsQueryKeys.dashboard({
        periodDays: 7,
        establishmentId: 'est-a',
      })
      queryClient.setQueryData(dashboardA, { total: 1 })
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      scheduleEstablishmentDashboardInvalidation(queryClient, 'est-a')
      vi.advanceTimersByTime(DASHBOARD_REALTIME_INVALIDATION_MS)
      expect(invalidateSpy).toHaveBeenCalledOnce()

      scheduleEstablishmentDashboardInvalidation(queryClient, 'est-a')
      vi.advanceTimersByTime(DASHBOARD_REALTIME_INVALIDATION_MS)
      expect(invalidateSpy).toHaveBeenCalledTimes(2)
    })
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

  it('invalidates execution comment queries without global keys', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    invalidateExecutionCommentQueries(queryClient, 'est-1', 'exec-1')

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['comments', 'action-plan-execution', 'est-1', 'exec-1'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['comments'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ['comments', 'action-plan-execution', 'est-1'],
    })
  })
})
