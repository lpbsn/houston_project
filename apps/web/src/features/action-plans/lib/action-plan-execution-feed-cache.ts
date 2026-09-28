import type { InfiniteData, QueryClient, QueryKey } from '@tanstack/react-query'

import type { ActionPlanExecutionFeedViewMode } from '../api'
import type {
  ActionPlanExecutionFeedItem,
  ActionPlanExecutionFeedItemWrapper,
  ActionPlanExecutionFeedResponse,
} from '../types'

const EXECUTION_FEED_VIEW_MODES: ActionPlanExecutionFeedViewMode[] = ['personal', 'general']

export type ActionPlanExecutionFeedSectionCountKey =
  | 'pinned'
  | 'pending_validation'
  | 'overdue'
  | 'in_progress'

export type ActionPlanExecutionFeedOptimisticSnapshot = {
  snapshots: {
    queryKey: QueryKey
    previous: InfiniteData<ActionPlanExecutionFeedResponse> | undefined
  }[]
}

function adjustSectionCounts(
  counts: ActionPlanExecutionFeedResponse['section_counts'],
  options: {
    isPinned: boolean
  },
): ActionPlanExecutionFeedResponse['section_counts'] {
  const next = { ...counts }
  const delta = options.isPinned ? 1 : -1
  next.pinned = Math.max(0, next.pinned + delta)
  return next
}

export function patchExecutionInFeedCache(
  queryClient: QueryClient,
  options: {
    establishmentId: string
    viewMode: ActionPlanExecutionFeedViewMode
    executionId: string
    patch: Partial<ActionPlanExecutionFeedItem>
    adjustSectionCountsForPin?: boolean
  },
): void {
  const queryKey = [
    'action-plans',
    'action-plan-execution-feed',
    options.establishmentId,
    options.viewMode,
  ] as const

  queryClient.setQueriesData<InfiniteData<ActionPlanExecutionFeedResponse>>({ queryKey }, (current) => {
    if (!current) {
      return current
    }

    let found: ActionPlanExecutionFeedItemWrapper | undefined
    for (const page of current.pages) {
      found = [...page.items, ...(page.pins ?? [])].find(
        (wrapper) => wrapper.action_plan_execution.id === options.executionId,
      )
      if (found) {
        break
      }
    }
    if (!found) {
      return current
    }

    const patched = {
      ...found,
      action_plan_execution: {
        ...found.action_plan_execution,
        ...options.patch,
      },
    }
    const requestedPinState = options.patch.is_pinned
    const movesCollection =
      typeof requestedPinState === 'boolean' &&
      found.action_plan_execution.is_pinned !== requestedPinState

    let pages = current.pages.map((page) => ({
      ...page,
      items: page.items
        .filter((wrapper) => wrapper.action_plan_execution.id !== options.executionId)
        .map((wrapper) =>
          wrapper.action_plan_execution.id === options.executionId ? patched : wrapper,
        ),
      pins: page.pins?.filter(
        (wrapper) => wrapper.action_plan_execution.id !== options.executionId,
      ),
    }))

    if (!movesCollection) {
      pages = current.pages.map((page) => ({
        ...page,
        items: page.items.map((wrapper) =>
          wrapper.action_plan_execution.id === options.executionId ? patched : wrapper,
        ),
        pins: page.pins?.map((wrapper) =>
          wrapper.action_plan_execution.id === options.executionId ? patched : wrapper,
        ),
      }))
    } else if (requestedPinState === true) {
      const pinsPageIndex = pages.findIndex((page) => Array.isArray(page.pins))
      if (pinsPageIndex >= 0) {
        const pinsPage = pages[pinsPageIndex]!
        pages[pinsPageIndex] = {
          ...pinsPage,
          pins: [...(pinsPage.pins ?? []), patched],
        }
      }
    }

    if (options.adjustSectionCountsForPin && movesCollection) {
      pages = pages.map((page) =>
        page.section_counts
          ? {
              ...page,
              section_counts: adjustSectionCounts(page.section_counts, {
                isPinned: requestedPinState === true,
              }),
            }
          : page,
      )
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
      queryKey: [
        'action-plans',
        'action-plan-execution-feed',
        establishmentId,
        viewMode,
      ],
    })
  }
}

export async function prepareActionPlanExecutionPinOptimisticUpdate(
  queryClient: QueryClient,
  options: {
    establishmentId: string
    executionId: string
    isPinned: boolean
  },
): Promise<ActionPlanExecutionFeedOptimisticSnapshot> {
  const snapshots: ActionPlanExecutionFeedOptimisticSnapshot['snapshots'] = []
  for (const viewMode of EXECUTION_FEED_VIEW_MODES) {
    const queryKey = [
      'action-plans',
      'action-plan-execution-feed',
      options.establishmentId,
      viewMode,
    ] as const
    await queryClient.cancelQueries({ queryKey })
    for (const [cachedQueryKey, previous] of queryClient.getQueriesData<
      InfiniteData<ActionPlanExecutionFeedResponse>
    >({ queryKey })) {
      snapshots.push({ queryKey: cachedQueryKey, previous })
    }
    patchExecutionInFeedCache(queryClient, {
      establishmentId: options.establishmentId,
      viewMode,
      executionId: options.executionId,
      patch: { is_pinned: options.isPinned },
      adjustSectionCountsForPin: true,
    })
  }
  return { snapshots }
}

export function restoreActionPlanExecutionPinOptimisticUpdate(
  queryClient: QueryClient,
  snapshot: ActionPlanExecutionFeedOptimisticSnapshot | undefined,
): void {
  if (!snapshot) {
    return
  }
  for (const entry of snapshot.snapshots) {
    if (entry.previous === undefined) {
      continue
    }
    queryClient.setQueryData(entry.queryKey, entry.previous)
  }
}

export function applyActionPlanExecutionPinSuccess(
  queryClient: QueryClient,
  options: {
    establishmentId: string
    executionId: string
    isPinned: boolean
    viewMode: ActionPlanExecutionFeedViewMode
    replacedExecutionId?: string
  },
): void {
  for (const mode of EXECUTION_FEED_VIEW_MODES) {
    patchExecutionInFeedCache(queryClient, {
      establishmentId: options.establishmentId,
      viewMode: mode,
      executionId: options.executionId,
      patch: { is_pinned: options.isPinned },
    })
    if (options.replacedExecutionId) {
      patchExecutionInFeedCache(queryClient, {
        establishmentId: options.establishmentId,
        viewMode: mode,
        executionId: options.replacedExecutionId,
        patch: { is_pinned: false },
      })
    }
  }
  invalidateActionPlanExecutionFeedViewModes(queryClient, options.establishmentId)
}
