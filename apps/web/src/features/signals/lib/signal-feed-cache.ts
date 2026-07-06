import type { InfiniteData, QueryClient } from '@tanstack/react-query'

import { signalsQueryKeys } from '../api'
import type {
  SignalDetail,
  SignalFeedFilters,
  SignalFeedItem,
  SignalFeedResponse,
  SignalViewMode,
} from '../types'

export type SignalQuickActionMutationKind = 'pin' | 'unpin' | 'urgency'

export type SignalQuickActionCacheContext = {
  viewMode: SignalViewMode
  filters: SignalFeedFilters
}

const SIGNAL_FEED_VIEW_MODES: SignalViewMode[] = ['personal', 'general']

export function feedItemPatchFromDetail(detail: SignalDetail): Partial<SignalFeedItem> {
  return {
    title: detail.title,
    structured_summary_short: detail.structured_summary_short,
    status: detail.status,
    urgency: detail.urgency,
    is_pinned: detail.is_pinned,
    affected_business_unit_key: detail.affected_business_unit_key ?? null,
    affected_business_unit_label: detail.affected_business_unit_label ?? null,
    responsible_business_unit_key: detail.responsible_business_unit_key ?? null,
    responsible_business_unit_label: detail.responsible_business_unit_label ?? null,
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

  queryClient.setQueryData<InfiniteData<SignalFeedResponse>>(queryKey, (current) => {
    if (!current) {
      return current
    }

    let updated = false
    const pages = current.pages.map((page) => {
      const items = page.items.map((item) => {
        if (item.id !== options.signalId) {
          return item
        }
        updated = true
        return { ...item, ...options.patch }
      })
      return items === page.items ? page : { ...page, items }
    })

    if (!updated) {
      return current
    }

    return { ...current, pages }
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
  const { establishmentId, signalId, detail, viewMode, filters, mutationKind } = options

  updateSignalDetailCache(queryClient, establishmentId, signalId, detail)

  if (mutationKind === 'urgency') {
    patchSignalInActiveFeedCache(queryClient, {
      establishmentId,
      viewMode,
      filters,
      signalId,
      patch: feedItemPatchFromDetail(detail),
    })
    return
  }

  invalidateSignalFeedViewModes(queryClient, establishmentId)
}
