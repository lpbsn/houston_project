import { describe, expect, it, vi } from 'vitest'

import { actionPlansQueryKeys } from '@/features/action-plans/api'
import { commentsQueryKeys } from '@/features/comments/api'
import { notificationsQueryKeys } from '@/features/notifications/api'
import { signalsQueryKeys } from '@/features/signals/api'
import { EMPTY_SIGNAL_FEED_FILTERS } from '@/features/signals/lib/signal-feed-filters'
import {
  invalidateActionPlanAssigneeSurfaces,
  invalidateActionPlanExecutionFeedQueries,
  invalidateActionPlanExecutionSurfaces,
  invalidateActionPlanMutationSurfaces,
  invalidateEstablishmentActionPlanCatalogQueries,
  invalidateEstablishmentNotificationQueries,
  invalidateEstablishmentSignalQueries,
  invalidateExecutionCommentQueries,
  invalidateSignalCommentQueries,
} from '@/lib/query-invalidation'
import { createTestQueryClient } from '@/test-utils'

const EST = 'est-parity'
const ENTITY = 'entity-parity'

function invalidatedPrefixes(queryClient: ReturnType<typeof createTestQueryClient>) {
  const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
  return {
    spy: invalidateSpy,
    prefixes(): readonly (readonly unknown[])[] {
      return invalidateSpy.mock.calls.map((call) => call[0]?.queryKey as readonly unknown[])
    },
  }
}

describe('query-invalidation factory parity', () => {
  it('invalidateEstablishmentSignalQueries matches signalsQueryKeys prefixes', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateEstablishmentSignalQueries(queryClient, EST)

    expect(prefixes()).toEqual(
      expect.arrayContaining([
        signalsQueryKeys.feed(EST, 'general', EMPTY_SIGNAL_FEED_FILTERS).slice(0, 3),
        signalsQueryKeys.detail(EST, ENTITY).slice(0, 3),
      ]),
    )
  })

  it('invalidateSignalCommentQueries matches commentsQueryKeys.signalList', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateSignalCommentQueries(queryClient, EST, ENTITY)

    expect(prefixes()).toEqual([commentsQueryKeys.signalList(EST, ENTITY)])
  })

  it('invalidateExecutionCommentQueries matches commentsQueryKeys.executionList', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateExecutionCommentQueries(queryClient, EST, ENTITY)

    expect(prefixes()).toEqual([commentsQueryKeys.executionList(EST, ENTITY)])
  })

  it('invalidateEstablishmentNotificationQueries matches notificationsQueryKeys.lists', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateEstablishmentNotificationQueries(queryClient, EST)

    expect(prefixes()).toEqual([notificationsQueryKeys.lists(EST)])
  })

  it('invalidateEstablishmentActionPlanCatalogQueries matches actionPlansQueryKeys prefixes', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateEstablishmentActionPlanCatalogQueries(queryClient, EST)

    expect(prefixes()).toEqual(
      expect.arrayContaining([
        actionPlansQueryKeys.catalog(EST).slice(0, 3),
        actionPlansQueryKeys.detail(EST, ENTITY).slice(0, 3),
      ]),
    )
  })

  it('invalidateActionPlanExecutionFeedQueries matches actionPlansQueryKeys.executionFeed', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateActionPlanExecutionFeedQueries(queryClient, EST)

    expect(prefixes()).toEqual([
      actionPlansQueryKeys.executionFeed(EST, 'personal').slice(0, 3),
    ])
  })

  it('invalidateActionPlanExecutionSurfaces matches execution feed and detail prefixes', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateActionPlanExecutionSurfaces(queryClient, EST, ENTITY)

    expect(prefixes()).toEqual(
      expect.arrayContaining([
        actionPlansQueryKeys.executionFeed(EST, 'personal').slice(0, 3),
        actionPlansQueryKeys.executionDetail(EST, ENTITY),
        signalsQueryKeys.feed(EST, 'general', EMPTY_SIGNAL_FEED_FILTERS).slice(0, 3),
        signalsQueryKeys.detail(EST, ENTITY).slice(0, 3),
      ]),
    )
  })

  it('invalidateActionPlanAssigneeSurfaces matches broad execution detail prefix', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateActionPlanAssigneeSurfaces(queryClient, EST)

    expect(prefixes()).toEqual([actionPlansQueryKeys.executionDetail(EST, ENTITY).slice(0, 3)])
  })

  it('invalidateActionPlanMutationSurfaces matches catalog prefixes', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateActionPlanMutationSurfaces(queryClient, EST, ENTITY)

    expect(prefixes()).toEqual(
      expect.arrayContaining([
        actionPlansQueryKeys.catalog(EST).slice(0, 3),
        actionPlansQueryKeys.detail(EST, ENTITY),
      ]),
    )
  })
})
