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
  patchExecutionInFeedCache,
  prepareActionPlanExecutionPinOptimisticUpdate,
  removeExecutionFromFeedCache,
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

describe('removeExecutionFromFeedCache', () => {
  it('reconciles pinned and business section counts after a realtime terminal removal', () => {
    const counts = {
      pinned: 1,
      pending_validation: 0,
      overdue: 1,
      in_progress: 2,
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
