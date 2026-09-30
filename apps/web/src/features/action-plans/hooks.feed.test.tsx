// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { actionPlansQueryKeys } from './api'
import { useActionPlanExecutionFeedQuery } from './hooks'
import {
  appendExecutionFeedWindow,
  executionFeedCacheFromPage,
  type ExecutionFeedCacheState,
} from './lib/action-plan-execution-feed-cache'
import type {
  ActionPlanExecutionFeedItem,
  ActionPlanExecutionFeedItemWrapper,
  ActionPlanExecutionFeedResponse,
} from './types'

const fetchActionPlanExecutionFeed = vi.fn()

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    fetchActionPlanExecutionFeed: (...args: unknown[]) =>
      fetchActionPlanExecutionFeed(...args),
  }
})

function wrapper(id: string): ActionPlanExecutionFeedItemWrapper {
  return {
    item_type: 'action_plan_execution',
    action_plan_execution: {
      id,
      title: id,
      status: 'in_progress',
      is_overdue: false,
      is_pinned: false,
    } as ActionPlanExecutionFeedItem,
  }
}

function page(
  id: string,
  nextCursor: string | null,
  hasMore: boolean,
): ActionPlanExecutionFeedResponse {
  return {
    items: [wrapper(id)],
    pins: [],
    scheduled: { count: 0, next: null },
    section_counts: {
      pinned: 0,
      pending_validation: 0,
      overdue: 0,
      in_progress: 4,
      done: 0,
      canceled: 0,
    },
    next_cursor: nextCursor,
    has_more: hasMore,
  }
}

function evictedCache(): ExecutionFeedCacheState {
  let state = executionFeedCacheFromPage(page('page-1', 'cursor-1', true))
  for (const [cursor, item, next] of [
    ['cursor-1', 'page-2', 'cursor-2'],
    ['cursor-2', 'page-3', 'cursor-3'],
    ['cursor-3', 'page-4', 'cursor-4'],
  ] as const) {
    state = {
      ...state,
      window: appendExecutionFeedWindow(
        state.window,
        page(item, next, true),
        cursor,
      ).window,
    }
  }
  return state
}

describe('useActionPlanExecutionFeedQuery continuations', () => {
  beforeEach(() => {
    fetchActionPlanExecutionFeed.mockReset()
  })

  it('keeps loadBehind and loadMore under one continuation ticket', async () => {
    const pending = new Map<string, (value: ActionPlanExecutionFeedResponse) => void>()
    fetchActionPlanExecutionFeed.mockImplementation(
      (
        _establishmentId: string,
        _viewMode: string,
        options: { cursor?: string } = {},
      ) => {
        if (!options.cursor) {
          return Promise.resolve(page('page-1', 'cursor-1', true))
        }
        return new Promise<ActionPlanExecutionFeedResponse>((resolve) => {
          pending.set(options.cursor!, resolve)
        })
      },
    )
    const queryClient = createTestQueryClient()
    const hook = renderHook(
      () => useActionPlanExecutionFeedQuery('est-1', 'personal'),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )
    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true))
    const queryKey = actionPlansQueryKeys.executionFeed('est-1', 'personal')
    queryClient.setQueryData(queryKey, evictedCache())

    act(() => {
      void hook.result.current.loadBehind()
      void hook.result.current.loadMore()
    })
    await waitFor(() => {
      expect(pending.has('cursor-1')).toBe(true)
      expect(pending.has('cursor-4')).toBe(true)
    })

    await act(async () => {
      pending.get('cursor-1')?.(page('stale-behind', 'cursor-2', true))
    })
    expect(hook.result.current.isLoadingMore).toBe(true)
    expect(
      queryClient
        .getQueryData<ExecutionFeedCacheState>(queryKey)
        ?.window.focus.flatMap((slot) =>
          slot.items.map((item) => item.action_plan_execution.id),
        ),
    ).not.toContain('stale-behind')

    await act(async () => {
      pending.get('cursor-4')?.(page('forward-wins', null, false))
    })
    await waitFor(() => expect(hook.result.current.isLoadingMore).toBe(false))
    expect(
      queryClient
        .getQueryData<ExecutionFeedCacheState>(queryKey)
        ?.window.focus.flatMap((slot) =>
          slot.items.map((item) => item.action_plan_execution.id),
        ),
    ).toContain('forward-wins')
  })
})
