import type { QueryClient } from '@tanstack/react-query'

import { signalsQueryKeys } from '../api'
import type {
  SignalDetail,
  SignalFeedFilters,
  SignalFeedItem,
  SignalFeedResponse,
  SignalViewMode,
} from '../types'

export type SignalQuickActionMutationKind = 'pin' | 'unpin'

export type SignalQuickActionCacheContext = {
  viewMode: SignalViewMode
  filters: SignalFeedFilters
}

const SIGNAL_FEED_VIEW_MODES: SignalViewMode[] = ['personal', 'general']

export const SIGNAL_FEED_MAX_PAGE_SIZE = 50
const SIGNAL_FEED_MAX_RESTORE_PAGES = 10

export function continuationPageSizeForRemainingDepth(remainingDepth: number): number {
  return Math.min(SIGNAL_FEED_MAX_PAGE_SIZE, Math.max(0, remainingDepth))
}

export function feedItemPatchFromDetail(detail: SignalDetail): Partial<SignalFeedItem> {
  return {
    title: detail.title,
    structured_summary_short: detail.structured_summary_short,
    status: detail.status,
    is_pinned: detail.is_pinned,
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

  queryClient.setQueryData<SignalFeedResponse>(queryKey, (current) => {
    if (!current) {
      return current
    }

    let updated = false
    const sections = current.sections.map((section) => {
      const items = section.items.map((item) => {
        if (item.id !== options.signalId) {
          return item
        }
        updated = true
        return { ...item, ...options.patch }
      })
      return items === section.items ? section : { ...section, items }
    })

    if (!updated) {
      return current
    }

    return { ...current, sections }
  })
}

export async function refillSignalFeedToLoadedDepth(
  firstPage: SignalFeedResponse,
  previous: SignalFeedResponse | undefined,
  fetchSectionPage: (
    status: string,
    cursor: string,
    pageSize: number,
  ) => Promise<SignalFeedResponse>,
): Promise<SignalFeedResponse> {
  if (!previous) {
    return firstPage
  }

  const previousByStatus = new Map(
    previous.sections.map((section) => [section.status, section]),
  )

  const sections = await Promise.all(
    firstPage.sections.map(async (section) => {
      const prior = previousByStatus.get(section.status)
      const target = prior?.items.length ?? 0
      if (!prior || target <= section.items.length) {
        return section
      }

      const seen = new Set(section.items.map((item) => item.id))
      const items = [...section.items]
      let nextCursor = section.next_cursor
      let hasMore = section.has_more
      let extraPages = 0

      while (
        items.length < target &&
        hasMore &&
        nextCursor &&
        extraPages < SIGNAL_FEED_MAX_RESTORE_PAGES
      ) {
        const pageSize = continuationPageSizeForRemainingDepth(target - items.length)
        if (pageSize <= 0) {
          break
        }
        extraPages += 1
        const page = await fetchSectionPage(section.status, nextCursor, pageSize)
        const incoming = page.sections.find((entry) => entry.status === section.status)
        if (!incoming) {
          break
        }
        for (const item of incoming.items) {
          if (seen.has(item.id)) {
            continue
          }
          seen.add(item.id)
          items.push(item)
          if (items.length >= target) {
            break
          }
        }
        nextCursor = incoming.next_cursor
        hasMore = incoming.has_more
      }

      return {
        ...section,
        items,
        next_cursor: nextCursor,
        has_more: hasMore,
      }
    }),
  )

  return { ...firstPage, sections }
}

export function appendSignalFeedSectionPage(
  queryClient: QueryClient,
  options: {
    establishmentId: string | null
    viewMode: SignalViewMode
    filters: SignalFeedFilters
    source?: 'establishment' | 'cross'
    status: string
    page: SignalFeedResponse
  },
): void {
  const queryKey =
    options.source === 'cross'
      ? signalsQueryKeys.crossFeed(options.filters)
      : options.establishmentId
        ? signalsQueryKeys.feed(options.establishmentId, options.viewMode, options.filters)
        : null
  if (queryKey == null) {
    return
  }

  const incoming = options.page.sections.find((section) => section.status === options.status)
  if (!incoming) {
    return
  }

  queryClient.setQueryData<SignalFeedResponse>(queryKey, (current) => {
    if (!current) {
      return current
    }
    return {
      ...current,
      sections: current.sections.map((section) => {
        if (section.status !== options.status) {
          return section
        }
        return {
          ...section,
          items: [...section.items, ...incoming.items],
          next_cursor: incoming.next_cursor,
          has_more: incoming.has_more,
        }
      }),
    }
  })
}

export function invalidateSignalFeedViewModes(
  queryClient: QueryClient,
  establishmentId: string,
  viewModes: SignalViewMode[] = SIGNAL_FEED_VIEW_MODES,
): void {
  for (const viewMode of viewModes) {
    void queryClient.invalidateQueries({
      queryKey: ['signals', 'feed', establishmentId, viewMode],
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
    mutationKind: SignalQuickActionMutationKind
  },
): void {
  const { establishmentId, signalId, detail } = options

  updateSignalDetailCache(queryClient, establishmentId, signalId, detail)
  invalidateSignalFeedViewModes(queryClient, establishmentId)
}
