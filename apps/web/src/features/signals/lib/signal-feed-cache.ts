import { hashKey, type QueryClient } from '@tanstack/react-query'

import {
  appendForwardPage,
  emptyFeedReadingWindow,
  hydratedItems,
  mapHydratedItems,
  removeHydratedItem,
  renderedItems,
  replaceWithFirstPage,
  windowHead,
  type FeedReadingWindow,
} from '@/lib/feed-reading-window'

import { signalsQueryKeys } from '../api'
import {
  selectedSignalFeedStatus,
  type SignalFeedStatusSelection,
} from './signal-feed-filters'
import type {
  SignalDetail,
  SignalFeedCounts,
  SignalFeedFilters,
  SignalFeedItem,
  SignalFeedPinsPage,
  SignalFeedResponse,
  SignalViewMode,
} from '../types'

export type SignalQuickActionCacheContext = {
  viewMode: SignalViewMode
  filters: SignalFeedFilters
}

export type SignalFeedCacheState = {
  readingWindow: FeedReadingWindow<SignalFeedItem>
  pinWindow: FeedReadingWindow<SignalFeedItem>
  counts: SignalFeedResponse['counts']
  applied_filters: SignalFeedResponse['applied_filters']
}

export type SignalFeedReadState = SignalFeedResponse & {
  readingWindow: FeedReadingWindow<SignalFeedItem>
  pinWindow: FeedReadingWindow<SignalFeedItem>
}

export type SignalFeedOptimisticSnapshot = {
  queryKey: ReturnType<typeof signalsQueryKeys.feed> | ReturnType<typeof signalsQueryKeys.crossFeed>
  previous: SignalFeedCacheState | undefined
}

const SIGNAL_FEED_VIEW_MODES: SignalViewMode[] = ['personal', 'general']
const PINNABLE_STATUSES = new Set(['open', 'interesting'])
const LIST_STATUSES = new Set(['open', 'in_progress', 'interesting'])
const STATUS_RANK: Record<string, number> = {
  open: 0,
  in_progress: 1,
  interesting: 2,
}

export function signalFeedQueryKey(options: {
  source?: 'establishment' | 'cross'
  establishmentId: string | null
  viewMode: SignalViewMode
  filters: SignalFeedFilters
}) {
  if (options.source === 'cross') {
    return signalsQueryKeys.crossFeed(options.filters)
  }
  if (options.establishmentId) {
    return signalsQueryKeys.feed(options.establishmentId, options.viewMode, options.filters)
  }
  return null
}

export function feedItemPatchFromDetail(detail: SignalDetail): Partial<SignalFeedItem> {
  return {
    title: detail.title,
    structured_summary_short: detail.structured_summary_short,
    status: detail.status,
    is_pinned: detail.is_pinned,
    pinned_at: detail.pinned_at ?? null,
    pinned_by_display_name: detail.pinned_by_display_name ?? null,
    affected_business_unit_id: detail.affected_business_unit_id ?? null,
    affected_business_unit_key: detail.affected_business_unit_key ?? null,
    affected_business_unit_label: detail.affected_business_unit_label ?? null,
    responsible_business_unit_id: detail.responsible_business_unit_id ?? null,
    responsible_business_unit_key: detail.responsible_business_unit_key ?? null,
    responsible_business_unit_label: detail.responsible_business_unit_label ?? null,
    activity_subject_id: detail.activity_subject_id ?? null,
    activity_subject_normalized_name: detail.activity_subject_normalized_name ?? null,
    activity_subject_label: detail.activity_subject_label ?? null,
    operational_unit_key: detail.operational_unit_key,
    location_text: detail.location_text,
    media_count: detail.media_count,
    last_activity_at: detail.last_activity_at,
    created_at: detail.created_at,
    reporter_display_name: detail.reporter_display_name ?? null,
    aggregation_count: detail.aggregation_count,
    permission_hints: detail.permission_hints,
  }
}

function isPinnableStatus(status: string): boolean {
  return PINNABLE_STATUSES.has(status)
}

function isListStatus(status: string): boolean {
  return LIST_STATUSES.has(status)
}

function compareSignalFeedListItems(left: SignalFeedItem, right: SignalFeedItem): number {
  const rank = (STATUS_RANK[left.status] ?? 3) - (STATUS_RANK[right.status] ?? 3)
  if (rank !== 0) {
    return rank
  }
  const activity =
    Date.parse(right.last_activity_at) - Date.parse(left.last_activity_at)
  if (activity !== 0) {
    return activity
  }
  const created = Date.parse(right.created_at) - Date.parse(left.created_at)
  if (created !== 0) {
    return created
  }
  return right.id.localeCompare(left.id)
}

function pinZoneIncludes(
  item: Pick<SignalFeedItem, 'status' | 'is_pinned'>,
  selection: SignalFeedStatusSelection,
): boolean {
  if (selection === 'in_progress' || !item.is_pinned || !isPinnableStatus(item.status)) {
    return false
  }
  return selection === 'all' || item.status === selection
}

function listIncludes(
  item: Pick<SignalFeedItem, 'status' | 'is_pinned'>,
  selection: SignalFeedStatusSelection,
): boolean {
  if (!isListStatus(item.status)) {
    return false
  }
  if (item.is_pinned && isPinnableStatus(item.status)) {
    return false
  }
  return selection === 'all' || item.status === selection
}

function countBucket(
  item: Pick<SignalFeedItem, 'status' | 'is_pinned'>,
  selection: SignalFeedStatusSelection,
): keyof SignalFeedCounts | null {
  if (item.is_pinned && isPinnableStatus(item.status)) {
    if (selection === 'in_progress') {
      return null
    }
    if (selection !== 'all' && item.status !== selection) {
      return null
    }
    return 'pinned'
  }
  if (item.status === 'open' || item.status === 'in_progress' || item.status === 'interesting') {
    return item.status
  }
  return null
}

function shiftCounts(
  counts: SignalFeedCounts | undefined,
  previous: Pick<SignalFeedItem, 'status' | 'is_pinned'> | null,
  next: Pick<SignalFeedItem, 'status' | 'is_pinned'> | null,
  selection: SignalFeedStatusSelection,
): SignalFeedCounts | undefined {
  if (!counts || !previous) {
    return counts
  }
  const updated = { ...counts }
  const from = countBucket(previous, selection)
  const to = next ? countBucket(next, selection) : null
  if (from) {
    updated[from] = Math.max(0, updated[from] - 1)
  }
  if (to) {
    updated[to] += 1
  }
  return updated
}

export function readSignalFeedCache(state: SignalFeedCacheState): SignalFeedReadState {
  const head = windowHead(state.readingWindow)
  const pinHead = windowHead(state.pinWindow)
  return {
    items: renderedItems(state.readingWindow, (item) => item.id),
    pins: renderedItems(state.pinWindow, (item) => item.id),
    counts: state.counts,
    next_cursor: head?.nextCursor ?? null,
    has_more: Boolean(head?.hasMore),
    pins_next_cursor: pinHead?.nextCursor ?? null,
    pins_has_more: Boolean(pinHead?.hasMore),
    applied_filters: state.applied_filters,
    readingWindow: state.readingWindow,
    pinWindow: state.pinWindow,
  }
}

export function signalFeedCacheFromFirstPage(
  page: SignalFeedResponse,
  generation = 1,
): SignalFeedCacheState {
  const readingWindow = replaceWithFirstPage(
    emptyFeedReadingWindow<SignalFeedItem>(),
    {
      requestCursor: null,
      nextCursor: page.next_cursor,
      hasMore: page.has_more,
      items: page.items,
    },
    generation,
  )
  const pinWindow = replaceWithFirstPage(
    emptyFeedReadingWindow<SignalFeedItem>(),
    {
      requestCursor: null,
      nextCursor: page.pins_next_cursor ?? null,
      hasMore: page.pins_has_more === true,
      items: page.pins ?? [],
    },
    generation,
  )
  return {
    counts: page.counts,
    applied_filters: page.applied_filters,
    readingWindow,
    pinWindow,
  }
}

function withPageOneItems<TItem>(
  window: FeedReadingWindow<TItem>,
  items: TItem[],
): FeedReadingWindow<TItem> {
  if (!window.pageOne) {
    return {
      ...window,
      pageOne: { requestCursor: null, nextCursor: null, hasMore: false, items },
    }
  }
  return { ...window, pageOne: { ...window.pageOne, items } }
}

export function reconcileSignalFeedItem(
  state: SignalFeedCacheState,
  filters: SignalFeedFilters,
  signalId: string,
  patch: Partial<SignalFeedItem>,
): SignalFeedCacheState {
  const selection = selectedSignalFeedStatus(filters)
  const pins = hydratedItems(state.pinWindow)
  const list = hydratedItems(state.readingWindow)
  const pinIndex = pins.findIndex((item) => item.id === signalId)
  const itemIndex = list.findIndex((item) => item.id === signalId)
  const found = pinIndex >= 0 ? pins[pinIndex] : itemIndex >= 0 ? list[itemIndex] : undefined
  if (!found) {
    return state
  }

  const next: SignalFeedItem = { ...found, ...patch, id: found.id }
  const structural = next.status !== found.status || next.is_pinned !== found.is_pinned
  if (!structural) {
    if (pinIndex >= 0) {
      return {
        ...state,
        pinWindow: mapHydratedItems(state.pinWindow, (item) =>
          item.id === signalId ? next : item,
        ),
      }
    }
    return {
      ...state,
      readingWindow: mapHydratedItems(state.readingWindow, (item) =>
        item.id === signalId ? next : item,
      ),
    }
  }

  const counts = shiftCounts(state.counts, found, next, selection)
  const cleared: SignalFeedCacheState = {
    ...state,
    counts,
    readingWindow: removeHydratedItem(state.readingWindow, signalId, (item) => item.id).window,
    pinWindow: removeHydratedItem(state.pinWindow, signalId, (item) => item.id).window,
  }
  const keepPinPosition =
    found.is_pinned &&
    next.is_pinned &&
    pinZoneIncludes(found, selection) &&
    pinZoneIncludes(next, selection)

  if (keepPinPosition && pinIndex >= 0) {
    const nextPins = [...(cleared.pinWindow.pageOne?.items ?? [])]
    nextPins.splice(Math.min(pinIndex, nextPins.length), 0, next)
    return {
      ...cleared,
      pinWindow: withPageOneItems(cleared.pinWindow, nextPins),
    }
  }
  if (pinZoneIncludes(next, selection)) {
    return {
      ...cleared,
      pinWindow: withPageOneItems(cleared.pinWindow, [
        next,
        ...(cleared.pinWindow.pageOne?.items ?? []),
      ]),
    }
  }
  if (listIncludes(next, selection)) {
    const pageOneItems = cleared.readingWindow.pageOne?.items ?? []
    return {
      ...cleared,
      readingWindow: withPageOneItems(
        cleared.readingWindow,
        [next, ...pageOneItems].sort(compareSignalFeedListItems),
      ),
    }
  }
  return cleared
}

export function patchSignalInActiveFeedCache(
  queryClient: QueryClient,
  options: {
    establishmentId: string
    viewMode: SignalViewMode
    filters: SignalFeedFilters
    signalId: string
    patch: Partial<SignalFeedItem>
  },
): void {
  const queryKey = signalsQueryKeys.feed(
    options.establishmentId,
    options.viewMode,
    options.filters,
  )
  queryClient.setQueryData<SignalFeedCacheState>(queryKey, (current) => {
    if (!current) {
      return current
    }
    return reconcileSignalFeedItem(current, options.filters, options.signalId, options.patch)
  })
}

export function appendSignalFeedPage(
  current: SignalFeedCacheState,
  page: SignalFeedResponse,
  requestedCursor = windowHead(current.readingWindow)?.nextCursor,
): { feed: SignalFeedCacheState; stalled: boolean } {
  if (!requestedCursor) {
    return { feed: current, stalled: false }
  }
  const appended = appendForwardPage(
    current.readingWindow,
    requestedCursor,
    {
      items: page.items,
      nextCursor: page.next_cursor,
      hasMore: page.has_more,
    },
    (item) => item.id,
  )
  if (appended.ignored) {
    return { feed: current, stalled: false }
  }
  return {
    stalled: appended.stalled,
    feed: {
      ...current,
      readingWindow: appended.window,
    },
  }
}

export function appendSignalFeedPinsPage(
  current: SignalFeedCacheState,
  page: SignalFeedPinsPage,
  requestedCursor = windowHead(current.pinWindow)?.nextCursor,
): { feed: SignalFeedCacheState; stalled: boolean } {
  if (!requestedCursor) {
    return { feed: current, stalled: false }
  }
  const appended = appendForwardPage(
    current.pinWindow,
    requestedCursor,
    {
      items: page.items,
      nextCursor: page.next_cursor,
      hasMore: page.has_more,
    },
    (item) => item.id,
  )
  if (appended.ignored) {
    return { feed: current, stalled: false }
  }
  return {
    stalled: appended.stalled,
    feed: {
      ...current,
      pinWindow: appended.window,
    },
  }
}

export function removeSignalFromFeedCache(
  state: SignalFeedCacheState,
  signalId: string,
): { feed: SignalFeedCacheState; neighborId: string | null } {
  const listItem = hydratedItems(state.readingWindow).find((item) => item.id === signalId)
  const pinItem = hydratedItems(state.pinWindow).find((item) => item.id === signalId)
  const list = removeHydratedItem(state.readingWindow, signalId, (item) => item.id)
  const pins = removeHydratedItem(state.pinWindow, signalId, (item) => item.id)
  let counts = state.counts
  if (counts && (listItem || pinItem)) {
    counts = { ...counts }
    if (pinItem) {
      counts.pinned = Math.max(0, counts.pinned - 1)
    } else if (
      listItem?.status === 'open' ||
      listItem?.status === 'in_progress' ||
      listItem?.status === 'interesting'
    ) {
      counts[listItem.status] = Math.max(0, counts[listItem.status] - 1)
    }
  }
  return {
    neighborId: list.neighborId ?? pins.neighborId,
    feed: {
      ...state,
      counts,
      readingWindow: list.window,
      pinWindow: pins.window,
    },
  }
}

export async function prepareSignalFeedOptimisticUpdate(
  queryClient: QueryClient,
  options: {
    establishmentId: string
    viewMode: SignalViewMode
    filters: SignalFeedFilters
  },
): Promise<SignalFeedOptimisticSnapshot> {
  const queryKey = signalsQueryKeys.feed(
    options.establishmentId,
    options.viewMode,
    options.filters,
  )
  await queryClient.cancelQueries({ queryKey })
  return {
    queryKey,
    previous: queryClient.getQueryData<SignalFeedCacheState>(queryKey),
  }
}

export function restoreSignalFeedOptimisticUpdate(
  queryClient: QueryClient,
  snapshot: SignalFeedOptimisticSnapshot | undefined,
): void {
  if (!snapshot || snapshot.previous === undefined) {
    return
  }
  queryClient.setQueryData(snapshot.queryKey, snapshot.previous)
}

export function invalidateSignalFeedViewModes(
  queryClient: QueryClient,
  establishmentId: string,
  viewModes: SignalViewMode[] = SIGNAL_FEED_VIEW_MODES,
  activeFeed?: SignalQuickActionCacheContext,
): void {
  const activeQueryHash = activeFeed
    ? hashKey(
        signalsQueryKeys.feed(
          establishmentId,
          activeFeed.viewMode,
          activeFeed.filters,
        ),
      )
    : null
  for (const viewMode of viewModes) {
    void queryClient.invalidateQueries({
      queryKey: ['signals', 'feed', establishmentId, viewMode],
      ...(activeQueryHash
        ? { predicate: (query) => query.queryHash !== activeQueryHash }
        : {}),
    })
  }
}

export function updateSignalDetailCache(
  queryClient: QueryClient,
  establishmentId: string,
  signalId: string,
  detail: SignalDetail,
): void {
  const detailKey = signalsQueryKeys.detail(establishmentId, signalId)
  if (!queryClient.getQueryData(detailKey)) {
    return
  }
  queryClient.setQueryData(detailKey, detail)
}

export function applySignalQuickActionSuccess(
  queryClient: QueryClient,
  options: {
    establishmentId: string
    signalId: string
    detail: SignalDetail
    viewMode: SignalViewMode
    filters: SignalFeedFilters
  },
): void {
  const { establishmentId, signalId, detail, viewMode, filters } = options

  updateSignalDetailCache(queryClient, establishmentId, signalId, detail)
  patchSignalInActiveFeedCache(queryClient, {
    establishmentId,
    viewMode,
    filters,
    signalId,
    patch: feedItemPatchFromDetail(detail),
  })
  invalidateSignalFeedViewModes(queryClient, establishmentId, SIGNAL_FEED_VIEW_MODES, {
    viewMode,
    filters,
  })
}
