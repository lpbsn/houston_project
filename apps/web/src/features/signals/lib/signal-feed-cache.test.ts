import { describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { signalsQueryKeys } from '../api'
import { EMPTY_SIGNAL_FEED_FILTERS } from './signal-feed-filters'
import type { SignalDetail, SignalFeedItem, SignalFeedResponse } from '../types'
import {
  applySignalQuickActionSuccess,
  feedItemPatchFromDetail,
  invalidateSignalFeedViewModes,
  patchSignalInActiveFeedCache,
  updateSignalDetailCache,
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
      can_archive: false,
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
      can_archive: false,
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

describe('patchSignalInActiveFeedCache', () => {
  it('patches the matching item across infinite query pages', () => {
    const queryClient = createTestQueryClient()
    const queryKey = signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS)
    const otherItem = buildFeedItem({ id: 'signal-2', title: 'Autre' })

    queryClient.setQueryData(queryKey, {
      pages: [
        {
          items: [buildFeedItem(), otherItem],
          next_cursor: 'cursor-1',
          has_more: true,
          applied_filters: { statuses: [], business_unit_ids: [], activity_subject_ids: [] },
        },
        {
          items: [buildFeedItem({ id: 'signal-3', title: 'Page 2' })],
          next_cursor: null,
          has_more: false,
          applied_filters: { statuses: [], business_unit_ids: [], activity_subject_ids: [] },
        },
      ],
      pageParams: [undefined, 'cursor-1'],
    })

    patchSignalInActiveFeedCache(queryClient, {
      establishmentId: EST,
      viewMode: 'personal',
      filters: EMPTY_SIGNAL_FEED_FILTERS,
      signalId: SIGNAL_ID,
      patch: { is_pinned: true },
    })

    const data = queryClient.getQueryData<{
      pages: SignalFeedResponse[]
    }>(queryKey)

    expect(data?.pages[0]?.items[0]?.is_pinned).toBe(true)
    expect(data?.pages[0]?.items[1]?.is_pinned).toBe(false)
    expect(data?.pages[1]?.items[0]?.is_pinned).toBe(false)
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
  it('invalidates feed view modes on pin without invalidating detail prefix', () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const detailKey = signalsQueryKeys.detail(EST, SIGNAL_ID)
    const detail = buildDetail({ is_pinned: true })

    queryClient.setQueryData(detailKey, buildDetail({ is_pinned: false }))

    applySignalQuickActionSuccess(queryClient, {
      establishmentId: EST,
      signalId: SIGNAL_ID,
      detail,
      viewMode: 'personal',
      filters: EMPTY_SIGNAL_FEED_FILTERS,
      mutationKind: 'pin',
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['signals', 'feed', EST, 'personal'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['signals', 'feed', EST, 'general'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ['signals', 'detail', EST],
    })
    expect(queryClient.getQueryData(detailKey)).toEqual(detail)
  })
})
