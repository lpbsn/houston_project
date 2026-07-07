import type { InfiniteData, QueryClient } from '@tanstack/react-query'

import { actionPlansQueryKeys, type ActionPlanExecutionFeedViewMode } from '../api'
import type { ActionPlanExecutionFeedItem, ActionPlanExecutionFeedResponse } from '../types'

const EXECUTION_FEED_VIEW_MODES: ActionPlanExecutionFeedViewMode[] = ['personal', 'general']

export function patchExecutionInFeedCache(
  queryClient: QueryClient,
  options: {
    establishmentId: string
    viewMode: ActionPlanExecutionFeedViewMode
    executionId: string
    patch: Partial<ActionPlanExecutionFeedItem>
  },
): void {
  const queryKey = actionPlansQueryKeys.executionFeed(
    options.establishmentId,
    options.viewMode,
  )

  queryClient.setQueryData<InfiniteData<ActionPlanExecutionFeedResponse>>(queryKey, (current) => {
    if (!current) {
      return current
    }

    let updated = false
    const pages = current.pages.map((page) => {
      const items = page.items.map((wrapper) => {
        if (wrapper.action_plan_execution.id !== options.executionId) {
          return wrapper
        }
        updated = true
        return {
          ...wrapper,
          action_plan_execution: {
            ...wrapper.action_plan_execution,
            ...options.patch,
          },
        }
      })
      return items === page.items ? page : { ...page, items }
    })

    if (!updated) {
      return current
    }

    return { ...current, pages }
  })
}

export function invalidateActionPlanExecutionFeedViewModes(
  queryClient: QueryClient,
  establishmentId: string,
  viewModes: ActionPlanExecutionFeedViewMode[] = EXECUTION_FEED_VIEW_MODES,
): void {
  for (const viewMode of viewModes) {
    void queryClient.invalidateQueries({
      queryKey: actionPlansQueryKeys.executionFeed(establishmentId, viewMode),
    })
  }
}

export function applyActionPlanExecutionPinSuccess(
  queryClient: QueryClient,
  options: {
    establishmentId: string
    executionId: string
    isPinned: boolean
    viewMode: ActionPlanExecutionFeedViewMode
  },
): void {
  for (const mode of EXECUTION_FEED_VIEW_MODES) {
    patchExecutionInFeedCache(queryClient, {
      establishmentId: options.establishmentId,
      viewMode: mode,
      executionId: options.executionId,
      patch: { is_pinned: options.isPinned },
    })
  }
  invalidateActionPlanExecutionFeedViewModes(queryClient, options.establishmentId)
}
