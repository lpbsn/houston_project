// @vitest-environment jsdom

import { QueryClient } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { actionPlansQueryKeys } from '../api'
import type { ActionPlanExecutionFeedItem, ActionPlanExecutionFeedResponse } from '../types'
import {
  registerFeedReadingSession,
  resetFeedReadingSessionsForTests,
} from '@/lib/feed-external-updates'

import {
  appendExecutionFeedWindow,
  applyActionPlanExecutionPinSuccess,
  executionFeedCacheFromPage,
  executionPinsCacheFromPage,
  patchExecutionInFeedCache,
  prepareActionPlanExecutionPinOptimisticUpdate,
  removeExecutionFromFeedCache,
  retainTerminalExecutionInFeedCache,
  retainTerminalExecutionInFeedCaches,
  type ExecutionFeedCacheState,
} from './action-plan-execution-feed-cache'

afterEach(() => {
  resetFeedReadingSessionsForTests()
})

function feedItem(
  id: string,
  partial: Partial<ActionPlanExecutionFeedItem> = {},
): ActionPlanExecutionFeedItem {
  return {
    id,
    title: id,
    description_short: '',
    status: 'in_progress',
    requires_validation: false,
    validated_at: null,
    validated_by_display_name: null,
    pilot_business_unit: {
      id: 'bu-1',
      specific_name: 'Cuisine',
      catalog_business_unit: { id: 'cbu-1', name: 'Cuisine', key: 'cuisine' },
    },
    involved_poles: [],
    signal_summary: null,
    assignees: [],
    start_at: null,
    end_at: null,
    all_day: false,
    visible_from: null,
    is_overdue: false,
    task_count: 0,
    treated_task_count: 0,
    task_preview: [],
    last_activity_at: '2026-01-01T00:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
    created_by_display_name: 'Alice',
    marked_done_at: null,
    marked_done_by_display_name: null,
    canceled_at: null,
    active_review: null,
    is_pinned: false,
    permission_hints: {
      can_pin: true,
      can_mark_done: false,
      can_validate: false,
      can_cancel: false,
      can_reopen: false,
      can_edit: false,
      can_comment: false,
    },
    ...partial,
  } as ActionPlanExecutionFeedItem
}

function page(
  items: ActionPlanExecutionFeedItem[],
  section_counts: ActionPlanExecutionFeedResponse['section_counts'],
  pins: ActionPlanExecutionFeedItem[] = [],
): ActionPlanExecutionFeedResponse {
  return {
    items: items.map((action_plan_execution) => ({
      item_type: 'action_plan_execution',
      action_plan_execution,
    })),
    pins: pins.map((action_plan_execution) => ({
      item_type: 'action_plan_execution',
      action_plan_execution,
    })),
    scheduled: { count: 0, next: null },
    section_counts,
    next_cursor: null,
    has_more: false,
  }
}

function cacheWithFocus(
  firstItems: ReturnType<typeof feedItem>[],
  counts: ActionPlanExecutionFeedResponse['section_counts'],
  nextItems: ReturnType<typeof feedItem>[],
): ExecutionFeedCacheState {
  const first = page(firstItems, counts)
  first.next_cursor = 'cursor-1'
  first.has_more = true
  const state = executionFeedCacheFromPage(first)
  const appended = appendExecutionFeedWindow(state.window, {
    items: nextItems.map((action_plan_execution) => ({
      item_type: 'action_plan_execution' as const,
      action_plan_execution,
    })),
    next_cursor: null,
    has_more: false,
  })
  return { ...state, window: appended.window }
}

describe('patchExecutionInFeedCache pin section_counts', () => {
  it('updates section counts when the matched execution is past the first page', () => {
    const queryClient = new QueryClient()
    const establishmentId = 'est-1'
    const viewMode = 'general' as const
    const counts = {
      pinned: 0,
      pending_validation: 0,
      overdue: 0,
      in_progress: 2,
      done: 0,
      canceled: 0,
    }
    queryClient.setQueryData(
      actionPlansQueryKeys.executionFeed(establishmentId, viewMode),
      cacheWithFocus([feedItem('page-0-only')], counts, [feedItem('target')]),
    )

    patchExecutionInFeedCache(queryClient, {
      establishmentId,
      viewMode,
      executionId: 'target',
      patch: { is_pinned: true },
      adjustSectionCountsForPin: true,
    })

    const data = queryClient.getQueryData<ExecutionFeedCacheState>(
      actionPlansQueryKeys.executionFeed(establishmentId, viewMode),
    )

    expect(data?.sectionCounts).toEqual({
      pinned: 1,
      pending_validation: 0,
      overdue: 0,
      in_progress: 2,
      done: 0,
      canceled: 0,
    })
    expect(data?.window.focus[0]?.items).toEqual([])
    expect(data?.pins.map((item) => item.action_plan_execution.id)).toEqual(['target'])
    expect(data?.window.pageOne?.items[0]?.action_plan_execution.is_pinned).toBe(false)
  })

  it('does not adjust section_counts when the pin state is unchanged', () => {
    const queryClient = new QueryClient()
    const establishmentId = 'est-1'
    const viewMode = 'personal' as const
    const counts = {
      pinned: 1,
      pending_validation: 0,
      overdue: 0,
      in_progress: 0,
      done: 0,
      canceled: 0,
    }
    queryClient.setQueryData(
      actionPlansQueryKeys.executionFeed(establishmentId, viewMode),
      executionFeedCacheFromPage(page([], counts, [feedItem('already-pinned', { is_pinned: true })])),
    )

    patchExecutionInFeedCache(queryClient, {
      establishmentId,
      viewMode,
      executionId: 'already-pinned',
      patch: { is_pinned: true },
      adjustSectionCountsForPin: true,
    })

    const data = queryClient.getQueryData<ExecutionFeedCacheState>(
      actionPlansQueryKeys.executionFeed(establishmentId, viewMode),
    )

    expect(data?.sectionCounts).toEqual(counts)
  })

  it('optimistically moves an unpinned execution from P to L', async () => {
    const queryClient = new QueryClient()
    const establishmentId = 'est-1'
    const counts = {
      pinned: 1,
      pending_validation: 0,
      overdue: 0,
      in_progress: 2,
      done: 0,
      canceled: 0,
    }
    queryClient.setQueryData(
      actionPlansQueryKeys.executionFeed(establishmentId, 'personal'),
      executionFeedCacheFromPage(
        page(
          [feedItem('existing-list-item')],
          counts,
          [feedItem('target', { is_pinned: true })],
        ),
      ),
    )

    await prepareActionPlanExecutionPinOptimisticUpdate(queryClient, {
      establishmentId,
      executionId: 'target',
      isPinned: false,
    })

    const data = queryClient.getQueryData<ExecutionFeedCacheState>(
      actionPlansQueryKeys.executionFeed(establishmentId, 'personal'),
    )

    expect(data?.pins).toEqual([])
    expect(data?.window.pageOne?.items.map((item) => item.action_plan_execution.id)).toEqual([
      'target',
      'existing-list-item',
    ])
    expect(data?.window.pageOne?.items[0]?.action_plan_execution.is_pinned).toBe(false)
    expect(data?.sectionCounts?.pinned).toBe(0)
  })

  it('replaces a pin without changing the pinned count', () => {
    const queryClient = new QueryClient()
    const establishmentId = 'est-1'
    const counts = {
      pinned: 3,
      pending_validation: 0,
      overdue: 0,
      in_progress: 1,
      done: 0,
      canceled: 0,
    }
    for (const viewMode of ['personal', 'general'] as const) {
      queryClient.setQueryData(
        actionPlansQueryKeys.executionFeed(establishmentId, viewMode),
        executionFeedCacheFromPage(
          page([feedItem('new-pin')], counts, [feedItem('old-pin', { is_pinned: true })]),
        ),
      )
    }

    applyActionPlanExecutionPinSuccess(queryClient, {
      establishmentId,
      executionId: 'new-pin',
      isPinned: true,
      viewMode: 'general',
      replacedExecutionId: 'old-pin',
    })

    for (const viewMode of ['personal', 'general'] as const) {
      const data = queryClient.getQueryData<ExecutionFeedCacheState>(
        actionPlansQueryKeys.executionFeed(establishmentId, viewMode),
      )
      expect(data?.sectionCounts?.pinned).toBe(3)
      expect(data?.window.pageOne?.items.map((item) => item.action_plan_execution.id)).toEqual([
        'old-pin',
      ])
      expect(data?.window.pageOne?.items[0]?.action_plan_execution.is_pinned).toBe(false)
      expect(data?.pins.map((item) => item.action_plan_execution.id)).toEqual(['new-pin'])
      expect(data?.pins[0]?.action_plan_execution.is_pinned).toBe(true)
    }
  })
})

describe('appendExecutionFeedWindow', () => {
  it('ignores a page fetched for a cursor the window head no longer exposes', () => {
    const counts = {
      pinned: 0,
      pending_validation: 0,
      overdue: 0,
      in_progress: 1,
      done: 0,
      canceled: 0,
    }
    const state = cacheWithFocus([feedItem('page-1')], counts, [feedItem('page-2')])
    const stale = appendExecutionFeedWindow(
      state.window,
      {
        items: [
          {
            item_type: 'action_plan_execution',
            action_plan_execution: feedItem('stale'),
          },
        ],
        next_cursor: 'cursor-9',
        has_more: true,
      },
      'cursor-1',
    )

    expect(stale.ignored).toBe(true)
    expect(stale.window.focus.flatMap((slot) => slot.items.map((item) => item.action_plan_execution.id))).toEqual([
      'page-2',
    ])
  })
})

function sectionTotal(counts: ActionPlanExecutionFeedResponse['section_counts']): number {
  return (
    counts.pending_validation +
    counts.overdue +
    counts.in_progress +
    counts.done +
    counts.canceled
  )
}

describe('retainTerminalExecutionInFeedCache', () => {
  const counts = {
    pinned: 1,
    pending_validation: 1,
    overdue: 1,
    in_progress: 2,
    done: 0,
    canceled: 0,
  }

  it('keeps a retained done execution in the all feed and moves its counters', () => {
    const current = executionFeedCacheFromPage(
      page(
        [feedItem('active')],
        counts,
        [feedItem('target', { is_pinned: true, is_overdue: true, end_at: '2026-01-01T00:00:00Z' })],
      ),
    )
    current.window.pageOne!.nextCursor = 'cursor-1'
    current.window.pageOne!.hasMore = true

    const retained = retainTerminalExecutionInFeedCache(current, {
      executionId: 'target',
      status: 'done',
      occurredAt: '2026-07-01T10:00:00Z',
      category: 'all',
    })

    expect(retained.pins).toEqual([])
    expect(retained.window.pageOne?.items.map((item) => item.action_plan_execution.id)).toEqual([
      'active',
      'target',
    ])
    expect(retained.window.pageOne?.items[1]?.action_plan_execution).toMatchObject({
      status: 'done',
      is_pinned: false,
      marked_done_at: '2026-07-01T10:00:00Z',
    })
    expect(retained.window.pageOne?.nextCursor).toBe('cursor-1')
    expect(retained.window.pageOne?.hasMore).toBe(true)
    expect(retained.sectionCounts).toEqual({
      pinned: 0,
      pending_validation: 1,
      overdue: 0,
      in_progress: 2,
      done: 1,
      canceled: 0,
    })
    expect(sectionTotal(retained.sectionCounts!)).toBe(sectionTotal(counts))
  })

  it('keeps a canceled execution on a later page without inventing an actor timestamp twice', () => {
    const first = page([feedItem('page-1')], counts)
    first.next_cursor = 'cursor-1'
    first.has_more = true
    const state = executionFeedCacheFromPage(first)
    const appended = appendExecutionFeedWindow(state.window, {
      items: [
        {
          item_type: 'action_plan_execution',
          action_plan_execution: feedItem('target', { status: 'pending_validation' }),
        },
      ],
      next_cursor: 'cursor-2',
      has_more: true,
    })
    const current = { ...state, window: appended.window }

    const retained = retainTerminalExecutionInFeedCache(current, {
      executionId: 'target',
      status: 'canceled',
      occurredAt: '2026-07-02T08:00:00Z',
      category: 'all',
    })

    const pages = [retained.window.pageOne, ...retained.window.focus]
    const target = pages
      .flatMap((slot) => slot?.items ?? [])
      .find((item) => item.action_plan_execution.id === 'target')
    expect(target?.action_plan_execution).toMatchObject({
      status: 'canceled',
      canceled_at: '2026-07-02T08:00:00Z',
    })
    expect(retained.window.focus[0]?.nextCursor).toBe('cursor-2')
    expect(retained.sectionCounts).toMatchObject({
      pending_validation: 0,
      canceled: 1,
      pinned: 1,
    })
    expect(sectionTotal(retained.sectionCounts!)).toBe(sectionTotal(counts))
  })

  it('drops the row from an operational category while keeping the global counters coherent', () => {
    const current = executionFeedCacheFromPage(
      page([feedItem('target', { status: 'in_progress' })], counts),
    )

    const retained = retainTerminalExecutionInFeedCache(current, {
      executionId: 'target',
      status: 'canceled',
      occurredAt: '2026-07-02T08:00:00Z',
      category: 'in_progress',
    })

    expect(retained.window.pageOne?.items).toEqual([])
    expect(retained.sectionCounts).toMatchObject({
      in_progress: 1,
      canceled: 1,
    })
    expect(sectionTotal(retained.sectionCounts!)).toBe(sectionTotal(counts))
  })

  it('does not move counters again when the execution is already terminal', () => {
    const doneCounts = { ...counts, in_progress: 1, done: 1 }
    const current = executionFeedCacheFromPage(
      page([feedItem('target', { status: 'done', marked_done_at: '2026-07-01T10:00:00Z' })], doneCounts),
    )

    const retained = retainTerminalExecutionInFeedCache(current, {
      executionId: 'target',
      status: 'done',
      occurredAt: '2026-07-03T10:00:00Z',
      category: 'all',
    })

    expect(retained.sectionCounts).toEqual(doneCounts)
    expect(retained.window.pageOne?.items[0]?.action_plan_execution.marked_done_at).toBe(
      '2026-07-01T10:00:00Z',
    )
  })
})

describe('retainTerminalExecutionInFeedCaches', () => {
  it('updates establishment and cross caches without touching another establishment', () => {
    const queryClient = new QueryClient()
    const counts = {
      pinned: 0,
      pending_validation: 0,
      overdue: 0,
      in_progress: 1,
      done: 0,
      canceled: 0,
    }
    queryClient.setQueryData(
      actionPlansQueryKeys.executionFeed('est-1', 'general', 'all'),
      executionFeedCacheFromPage(page([feedItem('target')], counts)),
    )
    queryClient.setQueryData(
      actionPlansQueryKeys.executionFeed('est-2', 'general', 'all'),
      executionFeedCacheFromPage(page([feedItem('target')], counts)),
    )
    queryClient.setQueryData(
      actionPlansQueryKeys.crossExecutionFeed('general', 'all'),
      executionFeedCacheFromPage(
        page([feedItem('other')], { ...counts, pinned: 1 }),
      ),
    )
    queryClient.setQueryData(
      actionPlansQueryKeys.crossExecutionFeedPins('general', 'in_progress'),
      executionPinsCacheFromPage({
        items: [
          {
            item_type: 'action_plan_execution',
            action_plan_execution: feedItem('target', { is_pinned: true }),
          },
        ],
        next_cursor: null,
        has_more: false,
      }),
    )

    retainTerminalExecutionInFeedCaches(queryClient, {
      establishmentId: 'est-1',
      executionId: 'target',
      status: 'done',
      occurredAt: '2026-07-04T09:00:00Z',
    })

    const establishment = queryClient.getQueryData<ExecutionFeedCacheState>(
      actionPlansQueryKeys.executionFeed('est-1', 'general', 'all'),
    )
    const otherEstablishment = queryClient.getQueryData<ExecutionFeedCacheState>(
      actionPlansQueryKeys.executionFeed('est-2', 'general', 'all'),
    )
    const cross = queryClient.getQueryData<ExecutionFeedCacheState>(
      actionPlansQueryKeys.crossExecutionFeed('general', 'all'),
    )
    const crossPins = queryClient.getQueryData<{ window: ExecutionFeedCacheState['window'] }>(
      actionPlansQueryKeys.crossExecutionFeedPins('general', 'in_progress'),
    )

    expect(establishment?.window.pageOne?.items[0]?.action_plan_execution.status).toBe('done')
    expect(establishment?.sectionCounts?.done).toBe(1)
    expect(establishment?.sectionCounts?.in_progress).toBe(0)
    expect(otherEstablishment?.window.pageOne?.items[0]?.action_plan_execution.status).toBe(
      'in_progress',
    )
    expect(cross?.window.pageOne?.items.map((item) => item.action_plan_execution.id)).toEqual([
      'other',
      'target',
    ])
    expect(cross?.window.pageOne?.items[1]?.action_plan_execution.status).toBe('done')
    expect(cross?.sectionCounts).toMatchObject({ pinned: 0, in_progress: 0, done: 1 })
    expect(crossPins?.window.pageOne?.items).toEqual([])
  })
})

describe('removeExecutionFromFeedCache', () => {
  it('reconciles pinned and business section counts after a realtime terminal removal', () => {
    const counts = {
      pinned: 1,
      pending_validation: 0,
      overdue: 1,
      in_progress: 2,
      done: 0,
      canceled: 0,
    }
    const current = executionFeedCacheFromPage(
      page(
        [feedItem('regular')],
        counts,
        [feedItem('target', { is_pinned: true, is_overdue: true })],
      ),
    )

    const removed = removeExecutionFromFeedCache(current, 'target')

    expect(removed.pins).toEqual([])
    expect(removed.sectionCounts).toEqual({
      pinned: 0,
      pending_validation: 0,
      overdue: 0,
      in_progress: 2,
      done: 0,
      canceled: 0,
    })
  })
})

describe('applyActionPlanExecutionPinSuccess invalidation', () => {
  it('defers the successful pin invalidation while a feed is being read', () => {
    const queryClient = new QueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const onDefer = vi.fn()
    registerFeedReadingSession({
      matches: (queryKey) =>
        queryKey[0] === 'action-plans' &&
        queryKey[1] === 'action-plan-execution-feed' &&
        queryKey[2] === 'est-1',
      atTop: () => false,
      interacting: () => false,
      onDefer,
      onRemove: vi.fn(),
    })

    applyActionPlanExecutionPinSuccess(queryClient, {
      establishmentId: 'est-1',
      executionId: 'target',
      isPinned: true,
      viewMode: 'personal',
    })

    expect(onDefer).toHaveBeenCalledTimes(2)
    expect(invalidateSpy).not.toHaveBeenCalled()
  })
})
