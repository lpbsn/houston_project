// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { signalsQueryKeys } from './api'
import { useSignalFeedQuery } from './hooks'
import { appendSignalFeedSectionPage } from './lib/signal-feed-cache'
import { EMPTY_SIGNAL_FEED_FILTERS } from './lib/signal-feed-filters'
import type { SignalFeedItem, SignalFeedResponse } from './types'

const EST = 'est-1'

const fetchSignalFeed = vi.fn()
const fetchCrossSignalFeed = vi.fn()

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    fetchSignalFeed: (...args: unknown[]) => fetchSignalFeed(...args),
    fetchCrossSignalFeed: (...args: unknown[]) => fetchCrossSignalFeed(...args),
  }
})

function buildFeedItem(overrides: Partial<SignalFeedItem> = {}): SignalFeedItem {
  return {
    id: 'signal-1',
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

function buildSection(
  status: string,
  itemIds: string[],
  nextCursor: string | null,
  hasMore: boolean,
) {
  return {
    status,
    items: itemIds.map((id) => buildFeedItem({ id, status })),
    next_cursor: nextCursor,
    has_more: hasMore,
  }
}

const appliedFilters = {
  statuses: [],
  business_unit_ids: [],
  activity_subject_ids: [],
}

const page1Ids = Array.from({ length: 25 }, (_, index) => `open-${index}`)
const page2Ids = Array.from({ length: 15 }, (_, index) => `open-extra-${index}`)

const firstPage: SignalFeedResponse = {
  sections: [
    buildSection('open', page1Ids, 'cursor-1', true),
    buildSection('resolved', ['resolved-1'], null, false),
  ],
  applied_filters: appliedFilters,
}

const page2: SignalFeedResponse = {
  sections: [buildSection('open', page2Ids, 'cursor-2', true)],
  applied_filters: appliedFilters,
}

function renderFeedHook() {
  const queryClient = createTestQueryClient()
  const hook = renderHook(
    () => useSignalFeedQuery(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS),
    {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    },
  )
  return { ...hook, queryClient }
}

describe('useSignalFeedQuery', () => {
  beforeEach(() => {
    fetchSignalFeed.mockReset()
    fetchCrossSignalFeed.mockReset()
  })

  it('keeps appended section items after invalidate refetch', async () => {
    fetchSignalFeed.mockImplementation(
      async (
        _establishmentId: string,
        _viewMode: string,
        _filters: unknown,
        options: { cursor?: string; pageSize?: number } = {},
      ) => {
        if (options.cursor) {
          return page2
        }
        return firstPage
      },
    )

    const { result, queryClient } = renderFeedHook()
    const queryKey = signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS)

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    appendSignalFeedSectionPage(queryClient, {
      establishmentId: EST,
      viewMode: 'personal',
      filters: EMPTY_SIGNAL_FEED_FILTERS,
      status: 'open',
      page: page2,
    })

    expect(queryClient.getQueryData<SignalFeedResponse>(queryKey)?.sections[0]?.items).toHaveLength(
      40,
    )

    await queryClient.invalidateQueries({ queryKey })

    await waitFor(() => {
      const data = queryClient.getQueryData<SignalFeedResponse>(queryKey)
      expect(data?.sections[0]?.items.map((item) => item.id)).toEqual([...page1Ids, ...page2Ids])
      expect(data?.sections[1]?.items.map((item) => item.id)).toEqual(['resolved-1'])
    })

    expect(fetchSignalFeed.mock.calls.some((call) => call[3]?.cursor == null)).toBe(true)
    const continuation = fetchSignalFeed.mock.calls.find((call) => call[3]?.cursor === 'cursor-1')
    expect(continuation?.[3]).toEqual({ cursor: 'cursor-1', pageSize: 15 })
    expect(continuation?.[2]).toEqual({ ...EMPTY_SIGNAL_FEED_FILTERS, statuses: ['open'] })
  })
})
