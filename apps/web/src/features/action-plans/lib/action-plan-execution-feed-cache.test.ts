// @vitest-environment jsdom

import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'

import { actionPlansQueryKeys } from '../api'
import type { ActionPlanExecutionFeedItem, ActionPlanExecutionFeedResponse } from '../types'

import { patchExecutionInFeedCache } from './action-plan-execution-feed-cache'

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
): ActionPlanExecutionFeedResponse {
  return {
    items: items.map((action_plan_execution) => ({
      item_type: 'action_plan_execution',
      action_plan_execution,
    })),
    scheduled_items: [],
    scheduled_count: 0,
    section_counts,
    next_cursor: null,
    has_more: false,
  }
}

describe('patchExecutionInFeedCache pin section_counts', () => {
  it('updates section_counts on every page, including pages before the matched item', () => {
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
    queryClient.setQueryData(actionPlansQueryKeys.executionFeed(establishmentId, viewMode), {
      pages: [
        page([feedItem('page-0-only')], counts),
        page([feedItem('target')], counts),
      ],
      pageParams: [undefined, 'cursor-1'],
    })

    patchExecutionInFeedCache(queryClient, {
      establishmentId,
      viewMode,
      executionId: 'target',
      patch: { is_pinned: true },
      adjustSectionCountsForPin: true,
    })

    const data = queryClient.getQueryData<{
      pages: ActionPlanExecutionFeedResponse[]
    }>(actionPlansQueryKeys.executionFeed(establishmentId, viewMode))

    expect(data?.pages[0]?.section_counts).toEqual({
      pinned: 1,
      pending_validation: 0,
      overdue: 0,
      in_progress: 1,
      done: 0,
      canceled: 0,
    })
    expect(data?.pages[1]?.section_counts).toEqual(data?.pages[0]?.section_counts)
    expect(data?.pages[1]?.items[0]?.action_plan_execution.is_pinned).toBe(true)
    expect(data?.pages[0]?.items[0]?.action_plan_execution.is_pinned).toBe(false)
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
    queryClient.setQueryData(actionPlansQueryKeys.executionFeed(establishmentId, viewMode), {
      pages: [page([feedItem('already-pinned', { is_pinned: true })], counts)],
      pageParams: [undefined],
    })

    patchExecutionInFeedCache(queryClient, {
      establishmentId,
      viewMode,
      executionId: 'already-pinned',
      patch: { is_pinned: true },
      adjustSectionCountsForPin: true,
    })

    const data = queryClient.getQueryData<{
      pages: ActionPlanExecutionFeedResponse[]
    }>(actionPlansQueryKeys.executionFeed(establishmentId, viewMode))

    expect(data?.pages[0]?.section_counts).toEqual(counts)
  })
})
