import type { InfiniteData, QueryClient, QueryKey } from '@tanstack/react-query'

import { actionPlansQueryKeys, type ActionPlanExecutionFeedViewMode } from '../api'
import type {
  ActionPlanExecutionFeedItem,
  ActionPlanExecutionFeedResponse,
} from '../types'

const EXECUTION_FEED_VIEW_MODES: ActionPlanExecutionFeedViewMode[] = ['personal', 'general']

export type ActionPlanExecutionFeedSectionCountKey =
  | 'pinned'
  | 'pending_validation'
  | 'overdue'
  | 'in_progress'
  | 'done'
  | 'canceled'

export type ActionPlanExecutionFeedOptimisticSnapshot = {
  snapshots: {
    queryKey: QueryKey
    previous: InfiniteData<ActionPlanExecutionFeedResponse> | undefined
  }[]
}

function originSectionCountKey(
  item: ActionPlanExecutionFeedItem,
): Exclude<ActionPlanExecutionFeedSectionCountKey, 'pinned'> | null {
  switch (item.status) {
    case 'pending_validation':
      return 'pending_validation'
    case 'in_progress':
      return item.is_overdue ? 'overdue' : 'in_progress'
    case 'done':
      return 'done'
    case 'canceled':
      return 'canceled'
    default:
      return null
  }
}

function adjustSectionCounts(
  counts: ActionPlanExecutionFeedResponse['section_counts'],
  options: {
    isPinned: boolean
    originKey: Exclude<ActionPlanExecutionFeedSectionCountKey, 'pinned'> | null
  },
): ActionPlanExecutionFeedResponse['section_counts'] {
  const next = { ...counts }
  const delta = options.isPinned ? 1 : -1
  next.pinned = Math.max(0, next.pinned + delta)
  if (options.originKey) {
    next[options.originKey] = Math.max(0, next[options.originKey] - delta)
  }
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
  const queryKey = actionPlansQueryKeys.executionFeed(
    options.establishmentId,
    options.viewMode,
  )

  queryClient.setQueryData<InfiniteData<ActionPlanExecutionFeedResponse>>(queryKey, (current) => {
    if (!current) {
      return current
    }

    let updated = false
    let originKey: Exclude<ActionPlanExecutionFeedSectionCountKey, 'pinned'> | null = null
    let pinTarget: boolean | null = null

    const pages = current.pages.map((page) => {
      const items = page.items.map((wrapper) => {
        if (wrapper.action_plan_execution.id !== options.executionId) {
          return wrapper
        }
        updated = true
        if (options.adjustSectionCountsForPin && typeof options.patch.is_pinned === 'boolean') {
          originKey = originSectionCountKey(wrapper.action_plan_execution)
          pinTarget = options.patch.is_pinned
        }
        return {
          ...wrapper,
          action_plan_execution: {
            ...wrapper.action_plan_execution,
            ...options.patch,
          },
        }
      })
      let nextPage = items === page.items ? page : { ...page, items }
      if (
        options.adjustSectionCountsForPin &&
        pinTarget != null &&
        page.section_counts
      ) {
        nextPage = {
          ...nextPage,
          section_counts: adjustSectionCounts(page.section_counts, {
            isPinned: pinTarget,
            originKey,
          }),
        }
        updated = true
      }
      return nextPage
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
    const queryKey = actionPlansQueryKeys.executionFeed(options.establishmentId, viewMode)
    await queryClient.cancelQueries({ queryKey })
    snapshots.push({
      queryKey,
      previous: queryClient.getQueryData<InfiniteData<ActionPlanExecutionFeedResponse>>(queryKey),
    })
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
