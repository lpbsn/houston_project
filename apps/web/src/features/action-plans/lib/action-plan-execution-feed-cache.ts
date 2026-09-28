import type { QueryClient, QueryKey } from '@tanstack/react-query'

import {
  appendForwardPage,
  emptyFeedReadingWindow,
  hydratedItems,
  mapHydratedItems,
  removeHydratedItem,
  replaceWithFirstPage,
  windowHead,
  type FeedReadingWindow,
} from '@/lib/feed-reading-window'
import { invalidateFeedListQuery } from '@/lib/query-invalidation'

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

export type ExecutionFeedCacheState = {
  window: FeedReadingWindow<ActionPlanExecutionFeedItemWrapper>
  pins: ActionPlanExecutionFeedItemWrapper[]
  sectionCounts: ActionPlanExecutionFeedResponse['section_counts'] | null
  scheduled: ActionPlanExecutionFeedResponse['scheduled'] | null
}

export type ExecutionPinsCacheState = {
  window: FeedReadingWindow<ActionPlanExecutionFeedItemWrapper>
}

export type ActionPlanExecutionFeedOptimisticSnapshot = {
  snapshots: {
    queryKey: QueryKey
    previous: ExecutionFeedCacheState | undefined
  }[]
}

function wrapperId(wrapper: ActionPlanExecutionFeedItemWrapper): string {
  return wrapper.action_plan_execution.id
}

export function executionFeedCacheFromPage(
  page: ActionPlanExecutionFeedResponse,
  generation = 1,
): ExecutionFeedCacheState {
  return {
    window: replaceWithFirstPage(
      emptyFeedReadingWindow<ActionPlanExecutionFeedItemWrapper>(),
      {
        requestCursor: null,
        nextCursor: page.next_cursor,
        hasMore: page.has_more,
        items: page.items,
      },
      generation,
    ),
    pins: page.pins ?? [],
    sectionCounts: page.section_counts ?? null,
    scheduled: page.scheduled ?? null,
  }
}

export function executionPinsCacheFromPage(
  page: { items: ActionPlanExecutionFeedItemWrapper[]; next_cursor: string | null; has_more: boolean },
  generation = 1,
): ExecutionPinsCacheState {
  return {
    window: replaceWithFirstPage(
      emptyFeedReadingWindow<ActionPlanExecutionFeedItemWrapper>(),
      {
        requestCursor: null,
        nextCursor: page.next_cursor,
        hasMore: page.has_more,
        items: page.items,
      },
      generation,
    ),
  }
}

export function appendExecutionFeedWindow<TPage extends {
  items: ActionPlanExecutionFeedItemWrapper[]
  next_cursor: string | null
  has_more: boolean
}>(
  window: FeedReadingWindow<ActionPlanExecutionFeedItemWrapper>,
  page: TPage,
  requestedCursor = windowHead(window)?.nextCursor ?? null,
) {
  if (!requestedCursor) {
    return { window, stalled: false as const, ignored: true as const }
  }
  return appendForwardPage(window, requestedCursor, {
    items: page.items,
    nextCursor: page.next_cursor,
    hasMore: page.has_more,
  }, wrapperId)
}

function patchWrapper(
  wrapper: ActionPlanExecutionFeedItemWrapper,
  patch: Partial<ActionPlanExecutionFeedItem>,
): ActionPlanExecutionFeedItemWrapper {
  return {
    ...wrapper,
    action_plan_execution: {
      ...wrapper.action_plan_execution,
      ...patch,
    },
  }
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

function executionSectionCountKey(
  item: ActionPlanExecutionFeedItem,
): Exclude<ActionPlanExecutionFeedSectionCountKey, 'pinned'> | null {
  if (item.status === 'pending_validation') {
    return 'pending_validation'
  }
  if (item.status === 'in_progress') {
    return item.is_overdue ? 'overdue' : 'in_progress'
  }
  return null
}

export function removeExecutionFromFeedCache(
  current: ExecutionFeedCacheState,
  executionId: string,
): ExecutionFeedCacheState {
  const list = hydratedItems(current.window)
  const listItem = list.find((wrapper) => wrapperId(wrapper) === executionId)
  const pinItem = current.pins.find((wrapper) => wrapperId(wrapper) === executionId)
  const found = pinItem ?? listItem
  if (!found) {
    return current
  }

  let sectionCounts = current.sectionCounts
  if (sectionCounts) {
    sectionCounts = { ...sectionCounts }
    if (pinItem) {
      sectionCounts.pinned = Math.max(0, sectionCounts.pinned - 1)
    }
    const section = executionSectionCountKey(found.action_plan_execution)
    if (section) {
      sectionCounts[section] = Math.max(0, sectionCounts[section] - 1)
    }
  }

  return {
    ...current,
    window: removeHydratedItem(current.window, executionId, wrapperId).window,
    pins: current.pins.filter((wrapper) => wrapperId(wrapper) !== executionId),
    sectionCounts,
  }
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

  queryClient.setQueriesData<ExecutionFeedCacheState>({ queryKey }, (current) => {
    if (!current?.window) {
      return current
    }

    const list = hydratedItems(current.window)
    const pinIndex = current.pins.findIndex((wrapper) => wrapperId(wrapper) === options.executionId)
    const listIndex = list.findIndex((wrapper) => wrapperId(wrapper) === options.executionId)
    const found = pinIndex >= 0 ? current.pins[pinIndex] : listIndex >= 0 ? list[listIndex] : undefined
    if (!found) {
      return current
    }

    const patched = patchWrapper(found, options.patch)
    const requestedPinState = options.patch.is_pinned
    const movesCollection =
      typeof requestedPinState === 'boolean' &&
      found.action_plan_execution.is_pinned !== requestedPinState

    if (!movesCollection) {
      return {
        ...current,
        pins: current.pins.map((wrapper) =>
          wrapperId(wrapper) === options.executionId ? patched : wrapper,
        ),
        window: mapHydratedItems(current.window, (wrapper) =>
          wrapperId(wrapper) === options.executionId ? patched : wrapper,
        ),
      }
    }

    const without = removeHydratedItem(current.window, options.executionId, wrapperId).window
    const pins = current.pins.filter((wrapper) => wrapperId(wrapper) !== options.executionId)
    let nextPins = pins
    let nextWindow = without
    if (requestedPinState === true) {
      nextPins = [...pins, patched]
    } else if (nextWindow.pageOne) {
      nextWindow = {
        ...nextWindow,
        pageOne: {
          ...nextWindow.pageOne,
          items: [patched, ...nextWindow.pageOne.items],
        },
      }
    }

    let sectionCounts = current.sectionCounts
    if (options.adjustSectionCountsForPin && sectionCounts) {
      sectionCounts = adjustSectionCounts(sectionCounts, {
        isPinned: requestedPinState === true,
      })
    }
    return {
      ...current,
      window: nextWindow,
      pins: nextPins,
      sectionCounts,
    }
  })
}

export function invalidateActionPlanExecutionFeedViewModes(
  queryClient: QueryClient,
  establishmentId: string,
  viewModes: ActionPlanExecutionFeedViewMode[] = EXECUTION_FEED_VIEW_MODES,
): void {
  for (const viewMode of viewModes) {
    invalidateFeedListQuery(queryClient, [
      'action-plans',
      'action-plan-execution-feed',
      establishmentId,
      viewMode,
    ])
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
    for (const [cachedQueryKey, previous] of queryClient.getQueriesData<ExecutionFeedCacheState>({
      queryKey,
    })) {
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
