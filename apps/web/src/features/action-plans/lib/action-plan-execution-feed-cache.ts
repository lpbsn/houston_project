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

import type {
  ActionPlanExecutionFeedCategory,
  ActionPlanExecutionFeedViewMode,
} from '../api'
import type {
  ActionPlanExecutionFeedItem,
  ActionPlanExecutionFeedItemWrapper,
  ActionPlanExecutionFeedResponse,
} from '../types'

const EXECUTION_FEED_VIEW_MODES: ActionPlanExecutionFeedViewMode[] = ['personal', 'general']
const EXECUTION_FEED_CATEGORIES = new Set<ActionPlanExecutionFeedCategory>([
  'all',
  'pending_validation',
  'overdue',
  'in_progress',
  'done',
  'canceled',
])

export type ExecutionFeedTerminalStatus = 'done' | 'canceled'

export type ActionPlanExecutionFeedSectionCountKey =
  | 'pinned'
  | 'pending_validation'
  | 'overdue'
  | 'in_progress'
  | 'done'
  | 'canceled'

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
  if (item.status === 'done') {
    return 'done'
  }
  if (item.status === 'canceled') {
    return 'canceled'
  }
  return null
}

function executionFeedCategoryFromQueryKey(
  queryKey: readonly unknown[],
): ActionPlanExecutionFeedCategory {
  const kind = queryKey[1]
  const raw =
    kind === 'cross-action-plan-execution-feed' ||
    kind === 'cross-action-plan-execution-feed-pins'
      ? queryKey[3]
      : queryKey[4]
  if (
    typeof raw === 'string' &&
    EXECUTION_FEED_CATEGORIES.has(raw as ActionPlanExecutionFeedCategory)
  ) {
    return raw as ActionPlanExecutionFeedCategory
  }
  return 'all'
}

function executionFeedViewModeFromQueryKey(
  queryKey: readonly unknown[],
): ActionPlanExecutionFeedViewMode | null {
  const kind = queryKey[1]
  const raw =
    kind === 'cross-action-plan-execution-feed' ||
    kind === 'cross-action-plan-execution-feed-pins'
      ? queryKey[2]
      : queryKey[3]
  return raw === 'personal' || raw === 'general' ? raw : null
}

function categoryKeepsTerminalStatus(
  category: ActionPlanExecutionFeedCategory,
  status: ExecutionFeedTerminalStatus,
): boolean {
  return category === 'all' || category === status
}

function categoryCountedPin(
  category: ActionPlanExecutionFeedCategory,
  item: ActionPlanExecutionFeedItem,
): boolean {
  if (category === 'all') {
    return true
  }
  if (category === 'pending_validation') {
    return item.status === 'pending_validation'
  }
  if (category === 'overdue') {
    return item.status === 'in_progress' && item.is_overdue
  }
  if (category === 'in_progress') {
    return item.status === 'in_progress' && !item.is_overdue
  }
  return item.status === category
}

function terminalExecutionPatch(
  item: ActionPlanExecutionFeedItem,
  status: ExecutionFeedTerminalStatus,
  occurredAt: string,
): Partial<ActionPlanExecutionFeedItem> {
  const patch: Partial<ActionPlanExecutionFeedItem> = {
    status,
    is_pinned: false,
    is_overdue: false,
  }
  if (status === 'canceled') {
    patch.canceled_at = item.canceled_at ?? occurredAt
    return patch
  }
  if (item.status === 'pending_validation' || item.validated_at != null) {
    patch.validated_at = item.validated_at ?? occurredAt
    return patch
  }
  patch.marked_done_at = item.marked_done_at ?? occurredAt
  return patch
}

function shiftTerminalSectionCounts(
  counts: ActionPlanExecutionFeedResponse['section_counts'],
  previous: ActionPlanExecutionFeedItem,
  status: ExecutionFeedTerminalStatus,
  wasPinned: boolean,
): ActionPlanExecutionFeedResponse['section_counts'] {
  const next = { ...counts }
  if (wasPinned) {
    next.pinned = Math.max(0, next.pinned - 1)
  }
  const from = executionSectionCountKey(previous)
  if (from === status) {
    return next
  }
  if (from) {
    next[from] = Math.max(0, next[from] - 1)
    next[status] += 1
  }
  return next
}

function appendUnpinnedToPageOne(
  window: FeedReadingWindow<ActionPlanExecutionFeedItemWrapper>,
  wrapper: ActionPlanExecutionFeedItemWrapper,
): FeedReadingWindow<ActionPlanExecutionFeedItemWrapper> {
  const without = removeHydratedItem(window, wrapperId(wrapper), wrapperId).window
  if (without.pageOne) {
    return {
      ...without,
      pageOne: {
        ...without.pageOne,
        items: [...without.pageOne.items, wrapper],
      },
    }
  }
  return {
    ...without,
    pageOne: {
      requestCursor: null,
      nextCursor: null,
      hasMore: false,
      items: [wrapper],
    },
  }
}

export function retainTerminalExecutionInFeedCache(
  current: ExecutionFeedCacheState,
  options: {
    executionId: string
    status: ExecutionFeedTerminalStatus
    occurredAt: string
    category: ActionPlanExecutionFeedCategory
  },
): ExecutionFeedCacheState {
  const list = hydratedItems(current.window)
  const listItem = list.find((wrapper) => wrapperId(wrapper) === options.executionId)
  const pinItem = current.pins.find((wrapper) => wrapperId(wrapper) === options.executionId)
  const found = pinItem ?? listItem
  if (!found) {
    return current
  }

  const previous = found.action_plan_execution
  const patched = patchWrapper(
    found,
    terminalExecutionPatch(previous, options.status, options.occurredAt),
  )
  const keep = categoryKeepsTerminalStatus(options.category, options.status)
  const sectionCounts = current.sectionCounts
    ? shiftTerminalSectionCounts(
        current.sectionCounts,
        previous,
        options.status,
        Boolean(pinItem),
      )
    : current.sectionCounts
  const pins = current.pins.filter((wrapper) => wrapperId(wrapper) !== options.executionId)

  if (!keep) {
    return {
      ...current,
      window: removeHydratedItem(current.window, options.executionId, wrapperId).window,
      pins,
      sectionCounts,
    }
  }

  return {
    ...current,
    window: listItem
      ? mapHydratedItems(current.window, (wrapper) =>
          wrapperId(wrapper) === options.executionId ? patched : wrapper,
        )
      : appendUnpinnedToPageOne(current.window, patched),
    pins,
    sectionCounts,
  }
}

export function retainTerminalExecutionInFeedCaches(
  queryClient: QueryClient,
  options: {
    establishmentId: string
    executionId: string
    status: ExecutionFeedTerminalStatus
    occurredAt: string
  },
): void {
  const feedEntries = [
    ...queryClient.getQueriesData<ExecutionFeedCacheState>({
      queryKey: ['action-plans', 'action-plan-execution-feed', options.establishmentId],
    }),
    ...queryClient.getQueriesData<ExecutionFeedCacheState>({
      queryKey: ['action-plans', 'cross-action-plan-execution-feed'],
    }),
  ]
  for (const [queryKey, current] of feedEntries) {
    if (!current?.window) {
      continue
    }
    const next = retainTerminalExecutionInFeedCache(current, {
      ...options,
      category: executionFeedCategoryFromQueryKey(queryKey),
    })
    if (next !== current) {
      queryClient.setQueryData(queryKey, next)
    }
  }

  const pinEntries = queryClient.getQueriesData<ExecutionPinsCacheState>({
    queryKey: ['action-plans', 'cross-action-plan-execution-feed-pins'],
  })
  for (const [queryKey, current] of pinEntries) {
    if (!current?.window) {
      continue
    }
    const pinItem = hydratedItems(current.window).find(
      (wrapper) => wrapperId(wrapper) === options.executionId,
    )
    if (!pinItem) {
      continue
    }
    const viewMode = executionFeedViewModeFromQueryKey(queryKey)
    queryClient.setQueryData<ExecutionPinsCacheState>(queryKey, {
      ...current,
      window: removeHydratedItem(current.window, options.executionId, wrapperId).window,
    })
    if (!viewMode) {
      continue
    }
    const patched = patchWrapper(
      pinItem,
      terminalExecutionPatch(pinItem.action_plan_execution, options.status, options.occurredAt),
    )
    const feedEntriesForMode = queryClient.getQueriesData<ExecutionFeedCacheState>({
      queryKey: ['action-plans', 'cross-action-plan-execution-feed', viewMode],
    })
    for (const [feedKey, feed] of feedEntriesForMode) {
      if (!feed?.window) {
        continue
      }
      const feedCategory = executionFeedCategoryFromQueryKey(feedKey)
      if (
        retainTerminalExecutionInFeedCache(feed, { ...options, category: feedCategory }) !== feed
      ) {
        continue
      }
      const keep = categoryKeepsTerminalStatus(feedCategory, options.status)
      const sectionCounts = feed.sectionCounts
        ? shiftTerminalSectionCounts(
            feed.sectionCounts,
            pinItem.action_plan_execution,
            options.status,
            categoryCountedPin(feedCategory, pinItem.action_plan_execution),
          )
        : feed.sectionCounts
      queryClient.setQueryData<ExecutionFeedCacheState>(feedKey, {
        ...feed,
        window: keep ? appendUnpinnedToPageOne(feed.window, patched) : feed.window,
        sectionCounts,
      })
    }
  }
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
