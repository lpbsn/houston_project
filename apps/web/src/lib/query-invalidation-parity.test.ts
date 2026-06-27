import { describe, expect, it, vi } from 'vitest'

import { actionsQueryKeys } from '@/features/actions/api'
import { checklistsQueryKeys } from '@/features/checklists/api'
import { commentsQueryKeys } from '@/features/comments/api'
import { notificationsQueryKeys } from '@/features/notifications/api'
import { signalsQueryKeys } from '@/features/signals/api'
import { EMPTY_SIGNAL_FEED_FILTERS } from '@/features/signals/lib/signal-feed-filters'
import {
  invalidateActionCommentQueries,
  invalidateActionMutationSurfaces,
  invalidateChecklistExecutionSurfaces,
  invalidateChecklistMutationSurfaces,
  invalidateEstablishmentActionQueries,
  invalidateEstablishmentChecklistQueries,
  invalidateEstablishmentNotificationQueries,
  invalidateEstablishmentSignalQueries,
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

  it('invalidateEstablishmentActionQueries matches actionsQueryKeys prefixes', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateEstablishmentActionQueries(queryClient, EST)

    expect(prefixes()).toEqual(
      expect.arrayContaining([
        actionsQueryKeys.feed(EST, 'personal').slice(0, 3),
        actionsQueryKeys.detail(EST, ENTITY).slice(0, 3),
      ]),
    )
  })

  it('invalidateEstablishmentChecklistQueries matches checklistsQueryKeys prefixes', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateEstablishmentChecklistQueries(queryClient, EST)

    expect(prefixes()).toEqual(
      expect.arrayContaining([
        checklistsQueryKeys.templates(EST).slice(0, 3),
        checklistsQueryKeys.templateDetail(EST, ENTITY).slice(0, 3),
        checklistsQueryKeys.assignments(EST),
        checklistsQueryKeys.executionDetail(EST, ENTITY).slice(0, 3),
      ]),
    )
  })

  it('invalidateSignalCommentQueries matches commentsQueryKeys.signalList', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateSignalCommentQueries(queryClient, EST, ENTITY)

    expect(prefixes()).toEqual([commentsQueryKeys.signalList(EST, ENTITY)])
  })

  it('invalidateActionCommentQueries matches commentsQueryKeys.actionList', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateActionCommentQueries(queryClient, EST, ENTITY)

    expect(prefixes()).toEqual([commentsQueryKeys.actionList(EST, ENTITY)])
  })

  it('invalidateEstablishmentNotificationQueries matches notificationsQueryKeys.lists', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateEstablishmentNotificationQueries(queryClient, EST)

    expect(prefixes()).toEqual([notificationsQueryKeys.lists(EST)])
  })

  it('invalidateActionMutationSurfaces matches action and signal prefixes', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateActionMutationSurfaces(queryClient, EST)

    expect(prefixes()).toEqual(
      expect.arrayContaining([
        actionsQueryKeys.feed(EST, 'personal').slice(0, 3),
        actionsQueryKeys.detail(EST, ENTITY).slice(0, 3),
        signalsQueryKeys.feed(EST, 'general', EMPTY_SIGNAL_FEED_FILTERS).slice(0, 3),
        signalsQueryKeys.detail(EST, ENTITY).slice(0, 3),
      ]),
    )
  })

  it('invalidateChecklistMutationSurfaces matches checklist and action prefixes', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateChecklistMutationSurfaces(queryClient, EST, ENTITY)

    expect(prefixes()).toEqual(
      expect.arrayContaining([
        checklistsQueryKeys.templates(EST).slice(0, 3),
        checklistsQueryKeys.templateDetail(EST, ENTITY),
        checklistsQueryKeys.assignments(EST),
        checklistsQueryKeys.executionDetail(EST, ENTITY).slice(0, 3),
        actionsQueryKeys.feed(EST, 'personal').slice(0, 3),
        actionsQueryKeys.detail(EST, ENTITY).slice(0, 3),
      ]),
    )
    expect(prefixes()).not.toEqual(
      expect.arrayContaining([signalsQueryKeys.feed(EST, 'general', EMPTY_SIGNAL_FEED_FILTERS).slice(0, 3)]),
    )
  })

  it('invalidateChecklistExecutionSurfaces matches execution detail and mutation surfaces', () => {
    const queryClient = createTestQueryClient()
    const { prefixes } = invalidatedPrefixes(queryClient)

    invalidateChecklistExecutionSurfaces(queryClient, EST, ENTITY)

    expect(prefixes()).toEqual(
      expect.arrayContaining([
        checklistsQueryKeys.executionDetail(EST, ENTITY),
        checklistsQueryKeys.templates(EST).slice(0, 3),
        checklistsQueryKeys.assignments(EST),
        actionsQueryKeys.feed(EST, 'personal').slice(0, 3),
        actionsQueryKeys.detail(EST, ENTITY).slice(0, 3),
      ]),
    )
  })
})
