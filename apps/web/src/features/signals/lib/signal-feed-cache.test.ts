import { describe, expect, it, vi } from 'vitest'
import { hashKey } from '@tanstack/react-query'

import { createTestQueryClient } from '@/test-utils'

import { signalsQueryKeys } from '../api'
import { EMPTY_SIGNAL_FEED_FILTERS, signalFeedFiltersForStatus } from './signal-feed-filters'
import type { SignalDetail, SignalFeedItem, SignalFeedResponse } from '../types'
import {
  appendSignalFeedPage,
  appendSignalFeedPinsPage,
  applySignalQuickActionSuccess,
  feedItemPatchFromDetail,
  invalidateSignalFeedViewModes,
  patchSignalInActiveFeedCache,
  readSignalFeedCache,
  reconcileSignalFeedItem,
  removeSignalFromFeedCache,
  signalFeedCacheFromFirstPage,
  updateSignalDetailCache,
  type SignalFeedCacheState,
} from './signal-feed-cache'

const EST = 'est-1'
const SIGNAL_ID = 'signal-1'

function buildFeedItem(overrides: Partial<SignalFeedItem> = {}): SignalFeedItem {
  return {
    id: SIGNAL_ID,
    title: 'Fuite',
    structured_summary_short: 'Short',
    status: 'open',
    routing_status: 'resolved',
    is_pinned: false,
    affected_business_unit_key: null,
    affected_business_unit_label: null,
    responsible_business_unit_key: null,
    responsible_business_unit_label: null,
    activity_subject_normalized_name: null,
    activity_subject_label: null,
    operational_unit_key: null,
    location_text: '',
    media_count: 0,
    aggregation_count: 0,
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    reporter_display_name: null,
    permission_hints: {
      can_pin: true,
      can_mark_interesting: false,
      can_cancel: false,
      can_resolve: false,
      can_create_linked_action_plan: false,
      can_qualify_routing: false,
    },
    ...overrides,
  }
}

function buildDetail(overrides: Partial<SignalDetail> = {}): SignalDetail {
  return {
    id: SIGNAL_ID,
    title: 'Fuite',
    structured_summary_short: 'Short',
    structured_summary: 'Long',
    status: 'open',
    routing_status: 'resolved',
    is_pinned: false,
    affected_business_unit_key: null,
    affected_business_unit_label: null,
    responsible_business_unit_key: null,
    responsible_business_unit_label: null,
    activity_subject_normalized_name: null,
    activity_subject_label: null,
    operational_unit_key: null,
    location_text: '',
    media_count: 0,
    aggregation_count: 0,
    last_activity_at: '2026-06-30T11:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    reporter_display_name: null,
    permission_hints: {
      can_pin: true,
      can_mark_interesting: false,
      can_cancel: false,
      can_resolve: false,
      can_create_linked_action_plan: false,
      can_qualify_routing: false,
      can_request_resolution: false,
      can_approve_resolution_request: false,
      can_reject_resolution_request: false,
      can_cancel_resolution_request: false,
    },
    source_context: { type: 'observation', observation_id: 'obs-1' },
    media_items: [],
    linked_action_plan_executions: [],
    resolution_request: null,
    resolution_request_events: [],
    marked_interesting_by_membership_id: null,
    marked_interesting_at: null,
    resolved_by_membership_id: null,
    resolved_at: null,
    resolution_origin: null,
    canceled_by_membership_id: null,
    canceled_at: null,
    ...overrides,
  }
}

describe('feedItemPatchFromDetail', () => {
  it('maps overlapping feed fields from detail', () => {
    const detail = buildDetail({ is_pinned: true })
    const patch = feedItemPatchFromDetail(detail)

    expect(patch.is_pinned).toBe(true)
    expect(patch.last_activity_at).toBe('2026-06-30T11:00:00Z')
  })

  it('preserves taxonomy ids and labels from detail', () => {
    const detail = buildDetail({
      affected_business_unit_id: 'bu-aff',
      affected_business_unit_key: 'communication',
      affected_business_unit_label: 'Communication',
      responsible_business_unit_id: null,
      responsible_business_unit_key: null,
      responsible_business_unit_label: null,
      activity_subject_id: null,
      activity_subject_normalized_name: null,
      activity_subject_label: null,
    })
    const patch = feedItemPatchFromDetail(detail)

    expect(patch.affected_business_unit_id).toBe('bu-aff')
    expect(patch.affected_business_unit_label).toBe('Communication')
    expect(patch.responsible_business_unit_id).toBeNull()
    expect(patch.activity_subject_id).toBeNull()
  })
})

const EMPTY_APPLIED_FILTERS = {
  statuses: [],
  business_unit_ids: [],
  activity_subject_ids: [],
}

const EMPTY_COUNTS = { open: 1, in_progress: 0, interesting: 0, pinned: 0, retained: 0 }

function buildFeed(overrides: Partial<SignalFeedResponse> = {}): SignalFeedResponse {
  return {
    items: [buildFeedItem()],
    pins: [],
    counts: EMPTY_COUNTS,
    next_cursor: null,
    has_more: false,
    applied_filters: EMPTY_APPLIED_FILTERS,
    ...overrides,
  }
}

describe('patchSignalInActiveFeedCache', () => {
  it('moves a newly pinned item out of the list and into the pin zone', () => {
    const queryClient = createTestQueryClient()
    const queryKey = signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS)
    const otherItem = buildFeedItem({ id: 'signal-2', title: 'Autre' })

    queryClient.setQueryData(
      queryKey,
      signalFeedCacheFromFirstPage(
        buildFeed({
          items: [buildFeedItem(), otherItem],
          counts: { open: 2, in_progress: 0, interesting: 0, pinned: 0, retained: 0 },
        }),
      ),
    )

    patchSignalInActiveFeedCache(queryClient, {
      establishmentId: EST,
      viewMode: 'personal',
      filters: EMPTY_SIGNAL_FEED_FILTERS,
      signalId: SIGNAL_ID,
      patch: { is_pinned: true },
    })

    const cache = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
    const data = cache ? readSignalFeedCache(cache) : undefined
    expect(data?.items.map((item) => item.id)).toEqual(['signal-2'])
    expect(data?.pins?.map((item) => item.id)).toEqual([SIGNAL_ID])
    expect(data?.pins?.[0]?.is_pinned).toBe(true)
    expect(data?.counts).toEqual({ open: 1, in_progress: 0, interesting: 0, pinned: 1, retained: 0 })
  })

  it('keeps an existing pin in place when the signal becomes interesting', () => {
    const queryClient = createTestQueryClient()
    const queryKey = signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS)
    const pinned = buildFeedItem({ id: SIGNAL_ID, is_pinned: true, status: 'open' })
    const otherPin = buildFeedItem({ id: 'pin-2', is_pinned: true, status: 'interesting' })

    queryClient.setQueryData(
      queryKey,
      signalFeedCacheFromFirstPage(
        buildFeed({
          items: [],
          pins: [pinned, otherPin],
          counts: { open: 0, in_progress: 0, interesting: 0, pinned: 2, retained: 0 },
        }),
      ),
    )

    const current = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
    const next = reconcileSignalFeedItem(current!, EMPTY_SIGNAL_FEED_FILTERS, SIGNAL_ID, {
      status: 'interesting',
    })
    const projected = readSignalFeedCache(next)

    expect(projected.pins?.map((item) => item.id)).toEqual([SIGNAL_ID, 'pin-2'])
    expect(projected.pins?.[0]?.status).toBe('interesting')
    expect(projected.pins?.[0]?.is_pinned).toBe(true)
    expect(next.counts?.pinned).toBe(2)
  })

  it('keeps a resolved signal in the unfiltered list and clears its pin', () => {
    const queryClient = createTestQueryClient()
    const queryKey = signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS)
    queryClient.setQueryData(queryKey, signalFeedCacheFromFirstPage(buildFeed()))

    patchSignalInActiveFeedCache(queryClient, {
      establishmentId: EST,
      viewMode: 'personal',
      filters: EMPTY_SIGNAL_FEED_FILTERS,
      signalId: SIGNAL_ID,
      patch: { status: 'resolved', is_pinned: false },
    })

    const cache = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
    const data = cache ? readSignalFeedCache(cache) : undefined
    expect(data?.items.map((item) => item.id)).toEqual([SIGNAL_ID])
    expect(data?.items[0]?.status).toBe('resolved')
    expect(data?.pins).toEqual([])
    expect(data?.counts?.open).toBe(0)
    expect(data?.counts?.retained).toBe(1)
  })

  it('drops a resolved signal from a status-filtered list', () => {
    const queryClient = createTestQueryClient()
    const filters = signalFeedFiltersForStatus(EMPTY_SIGNAL_FEED_FILTERS, 'open')
    const queryKey = signalsQueryKeys.feed(EST, 'personal', filters)
    queryClient.setQueryData(queryKey, signalFeedCacheFromFirstPage(buildFeed()))

    patchSignalInActiveFeedCache(queryClient, {
      establishmentId: EST,
      viewMode: 'personal',
      filters,
      signalId: SIGNAL_ID,
      patch: { status: 'resolved', is_pinned: false },
    })

    const cache = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
    const data = cache ? readSignalFeedCache(cache) : undefined
    expect(data?.items).toEqual([])
    expect(data?.pins).toEqual([])
    expect(data?.counts?.open).toBe(0)
    expect(data?.counts?.retained).toBe(0)
  })

  it('keeps the global category order after an optimistic status transition', () => {
    const open = buildFeedItem({
      id: 'open-1',
      status: 'open',
      last_activity_at: '2026-06-30T09:00:00Z',
    })
    const moved = buildFeedItem({
      id: SIGNAL_ID,
      status: 'open',
      last_activity_at: '2026-06-30T10:00:00Z',
    })
    const inProgress = buildFeedItem({
      id: 'progress-1',
      status: 'in_progress',
      last_activity_at: '2026-06-30T08:00:00Z',
    })
    const interesting = buildFeedItem({
      id: 'interesting-1',
      status: 'interesting',
      last_activity_at: '2026-06-30T07:00:00Z',
    })
    const next = readSignalFeedCache(reconcileSignalFeedItem(
      signalFeedCacheFromFirstPage(
        buildFeed({ items: [moved, open, inProgress, interesting] }),
      ),
      EMPTY_SIGNAL_FEED_FILTERS,
      SIGNAL_ID,
      { status: 'interesting' },
    ))

    expect(next.items.map((item) => item.id)).toEqual([
      'open-1',
      'progress-1',
      SIGNAL_ID,
      'interesting-1',
    ])
  })
})

describe('appendSignalFeedPage', () => {
  it('appends list items and keeps pins and counts from the first page', () => {
    const current = signalFeedCacheFromFirstPage(
      buildFeed({
        items: [buildFeedItem({ id: 'open-1' })],
        pins: [buildFeedItem({ id: 'pin-1', is_pinned: true })],
        counts: { open: 2, in_progress: 0, interesting: 0, pinned: 1, retained: 0 },
        next_cursor: 'cursor-1',
        has_more: true,
      }),
    )
    const page = buildFeed({
      items: [buildFeedItem({ id: 'open-2', status: 'in_progress' })],
      pins: [],
      counts: undefined,
      next_cursor: 'cursor-2',
      has_more: true,
    })

    const appended = appendSignalFeedPage(current, page)
    const projected = readSignalFeedCache(appended.feed)

    expect(appended.stalled).toBe(false)
    expect(projected.items.map((item) => item.id)).toEqual(['open-1', 'open-2'])
    expect(projected.pins?.map((item) => item.id)).toEqual(['pin-1'])
    expect(appended.feed.counts).toEqual(current.counts)
    expect(projected.next_cursor).toBe('cursor-2')
  })
})

describe('appendSignalFeedPinsPage', () => {
  it('appends cross pins without replacing the list', () => {
    const current = signalFeedCacheFromFirstPage(
      buildFeed({
        items: [buildFeedItem({ id: 'open-1' })],
        pins: [buildFeedItem({ id: 'pin-1', is_pinned: true })],
        pins_next_cursor: 'pins-1',
        pins_has_more: true,
      }),
    )
    const appended = appendSignalFeedPinsPage(current, {
      items: [buildFeedItem({ id: 'pin-2', is_pinned: true })],
      next_cursor: null,
      has_more: false,
    })

    const projected = readSignalFeedCache(appended.feed)
    expect(projected.items.map((item) => item.id)).toEqual(['open-1'])
    expect(projected.pins?.map((item) => item.id)).toEqual(['pin-1', 'pin-2'])
    expect(projected.pins_has_more).toBe(false)
  })
})

describe('removeSignalFromFeedCache', () => {
  it('decrements the list status count for a realtime terminal removal', () => {
    const removed = removeSignalFromFeedCache(
      signalFeedCacheFromFirstPage(
        buildFeed({
          items: [
            buildFeedItem({ id: 'signal-1', status: 'open' }),
            buildFeedItem({ id: 'signal-2', status: 'open' }),
          ],
          counts: { open: 2, in_progress: 0, interesting: 0, pinned: 0, retained: 0 },
        }),
      ),
      'signal-1',
    )

    expect(readSignalFeedCache(removed.feed).items.map((item) => item.id)).toEqual(['signal-2'])
    expect(removed.feed.counts).toEqual({
      open: 1,
      in_progress: 0,
      interesting: 0,
      pinned: 0,
      retained: 0,
    })
  })

  it('decrements only the pinned count when a pinned signal is removed', () => {
    const removed = removeSignalFromFeedCache(
      signalFeedCacheFromFirstPage(
        buildFeed({
          items: [],
          pins: [buildFeedItem({ is_pinned: true })],
          counts: { open: 4, in_progress: 2, interesting: 1, pinned: 1, retained: 0 },
        }),
      ),
      SIGNAL_ID,
    )

    expect(readSignalFeedCache(removed.feed).pins).toEqual([])
    expect(removed.feed.counts).toEqual({
      open: 4,
      in_progress: 2,
      interesting: 1,
      pinned: 0,
      retained: 0,
    })
  })
})

describe('invalidateSignalFeedViewModes', () => {
  it('invalidates personal and general feed prefixes without detail queries', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    invalidateSignalFeedViewModes(queryClient, EST)

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['signals', 'feed', EST, 'personal'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['signals', 'feed', EST, 'general'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ['signals', 'detail', EST],
    })
  })
})

describe('updateSignalDetailCache', () => {
  it('sets detail data only when detail query is already cached', () => {
    const queryClient = createTestQueryClient()
    const detailKey = signalsQueryKeys.detail(EST, SIGNAL_ID)
    const detail = buildDetail()

    updateSignalDetailCache(queryClient, EST, SIGNAL_ID, detail)
    expect(queryClient.getQueryData(detailKey)).toBeUndefined()

    queryClient.setQueryData(detailKey, buildDetail({ is_pinned: false }))
    updateSignalDetailCache(queryClient, EST, SIGNAL_ID, detail)

    expect(queryClient.getQueryData(detailKey)).toEqual(detail)
  })
})

describe('applySignalQuickActionSuccess', () => {
  it('patches active feed and invalidates feed view modes without detail prefix', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const detailKey = signalsQueryKeys.detail(EST, SIGNAL_ID)
    const feedKey = signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS)
    const detail = buildDetail({ is_pinned: true, title: 'Pinned title' })

    queryClient.setQueryData(detailKey, buildDetail({ is_pinned: false }))
    queryClient.setQueryData(
      feedKey,
      signalFeedCacheFromFirstPage(
        buildFeed({
          items: [
            buildFeedItem({ is_pinned: false, title: 'Old title' }),
            buildFeedItem({ id: 'loaded-page-2' }),
          ],
          next_cursor: 'cursor-after-page-2',
          has_more: true,
        }),
      ),
    )

    applySignalQuickActionSuccess(queryClient, {
      establishmentId: EST,
      signalId: SIGNAL_ID,
      detail,
      viewMode: 'personal',
      filters: EMPTY_SIGNAL_FEED_FILTERS,
    })

    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['signals', 'feed', EST, 'personal'],
    }))
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['signals', 'feed', EST, 'general'],
    }))
    const personalInvalidation = invalidateSpy.mock.calls.find(
      ([filters]) => filters.queryKey?.[3] === 'personal',
    )?.[0]
    expect(personalInvalidation?.predicate?.({
      queryHash: hashKey(feedKey),
    } as never)).toBe(false)
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ['signals', 'detail', EST],
    })
    expect(queryClient.getQueryData(detailKey)).toEqual(detail)
    const cache = queryClient.getQueryData<SignalFeedCacheState>(feedKey)
    const feed = cache ? readSignalFeedCache(cache) : undefined
    expect(feed?.pins?.[0]?.is_pinned).toBe(true)
    expect(feed?.pins?.[0]?.title).toBe('Pinned title')
    expect(feed?.items.map((item) => item.id)).toEqual(['loaded-page-2'])
    expect(feed?.next_cursor).toBe('cursor-after-page-2')
    expect(feed?.has_more).toBe(true)
  })
})
