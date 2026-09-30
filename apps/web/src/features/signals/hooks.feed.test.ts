// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { signalsQueryKeys } from './api'
import { useLoadMoreSignalFeed, useRefreshSignalFeed, useSignalFeedQuery } from './hooks'
import {
  readSignalFeedCache,
  signalFeedCacheFromFirstPage,
  type SignalFeedCacheState,
} from './lib/signal-feed-cache'
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

const appliedFilters = {
  statuses: [],
  business_unit_ids: [],
  activity_subject_ids: [],
}

const page1Ids = Array.from({ length: 25 }, (_, index) => `open-${index}`)
const page2Ids = Array.from({ length: 15 }, (_, index) => `open-extra-${index}`)

const firstPage: SignalFeedResponse = {
  items: page1Ids.map((id) => buildFeedItem({ id, status: 'open' })),
  pins: [buildFeedItem({ id: 'pin-1', is_pinned: true, title: 'Épinglée' })],
  counts: { open: 40, in_progress: 0, interesting: 0, pinned: 1, retained: 0, resolved: 0, canceled: 0 },
  next_cursor: 'cursor-1',
  has_more: true,
  applied_filters: appliedFilters,
}

const page2: SignalFeedResponse = {
  items: page2Ids.map((id) => buildFeedItem({ id, status: 'in_progress' })),
  next_cursor: 'cursor-2',
  has_more: false,
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

  it('loads the first page without refilling later pages after invalidate', async () => {
    fetchSignalFeed.mockResolvedValue(firstPage)

    const { result, queryClient } = renderFeedHook()
    const queryKey = signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS)

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    const initialCache = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
    expect(initialCache).not.toHaveProperty('items')
    expect(initialCache).not.toHaveProperty('pins')
    expect(initialCache?.readingWindow.pageOne?.items).toHaveLength(25)
    expect(initialCache?.pinWindow.pageOne?.items).toHaveLength(1)

    await queryClient.invalidateQueries({ queryKey })

    await waitFor(() => {
      expect(fetchSignalFeed).toHaveBeenCalledTimes(2)
    })

    const cache = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
    const data = cache ? readSignalFeedCache(cache) : undefined
    expect(data?.items.map((item) => item.id)).toEqual(page1Ids)
    expect(data?.pins?.map((item) => item.id)).toEqual(['pin-1'])
    expect(fetchSignalFeed.mock.calls.every((call) => call[3] == null || call[3].cursor == null)).toBe(
      true,
    )
  })

  it('appends the next list page and keeps the first-page pins', async () => {
    fetchSignalFeed.mockImplementation(
      async (
        _establishmentId: string,
        _viewMode: string,
        _filters: unknown,
        options: { cursor?: string } = {},
      ) => (options.cursor ? page2 : firstPage),
    )

    const queryClient = createTestQueryClient()
    const hook = renderHook(
      () => ({
        feed: useSignalFeedQuery(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS),
        loadMore: useLoadMoreSignalFeed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS),
      }),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    await waitFor(() => {
      expect(hook.result.current.feed.isSuccess).toBe(true)
    })

    hook.result.current.loadMore.mutate()

    await waitFor(() => {
      expect(hook.result.current.loadMore.isSuccess).toBe(true)
    })

    const cache = queryClient.getQueryData<SignalFeedCacheState>(
      signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS),
    )
    const data = cache ? readSignalFeedCache(cache) : undefined
    expect(data?.items.map((item) => item.id)).toEqual([...page1Ids, ...page2Ids])
    expect(data?.pins?.map((item) => item.id)).toEqual(['pin-1'])
    expect(data?.counts?.pinned).toBe(1)
    expect(data?.next_cursor).toBe('cursor-2')
    expect(data?.has_more).toBe(false)
  })

  it('ignores a continuation response from an older generation', async () => {
    let resolveContinuation: ((page: SignalFeedResponse) => void) | undefined
    fetchSignalFeed.mockImplementation(
      (
        _establishmentId: string,
        _viewMode: string,
        _filters: unknown,
        options: { cursor?: string } = {},
      ) =>
        options.cursor
          ? new Promise<SignalFeedResponse>((resolve) => {
              resolveContinuation = resolve
            })
          : Promise.resolve(firstPage),
    )

    const queryClient = createTestQueryClient()
    const hook = renderHook(
      () => ({
        feed: useSignalFeedQuery(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS),
        loadMore: useLoadMoreSignalFeed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS),
      }),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )
    await waitFor(() => expect(hook.result.current.feed.isSuccess).toBe(true))

    act(() => hook.result.current.loadMore.mutate())
    await waitFor(() => expect(resolveContinuation).toBeDefined())

    const queryKey = signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS)
    queryClient.setQueryData(
      queryKey,
      signalFeedCacheFromFirstPage(
        {
          ...firstPage,
          items: [buildFeedItem({ id: 'refreshed' })],
        },
        2,
      ),
    )
    await act(async () => {
      resolveContinuation?.(page2)
    })

    await waitFor(() => expect(hook.result.current.loadMore.isSuccess).toBe(true))
    const data = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
    expect(readSignalFeedCache(data!).items.map((item) => item.id)).toEqual(['refreshed'])
    expect(data?.readingWindow.generation).toBe(2)
  })

  it('exposes and retries a stalled continuation from the reading window', async () => {
    let continuationAttempts = 0
    fetchSignalFeed.mockImplementation(
      async (
        _establishmentId: string,
        _viewMode: string,
        _filters: unknown,
        options: { cursor?: string } = {},
      ) =>
        options.cursor
          ? ++continuationAttempts === 1
            ? {
                items: [],
                next_cursor: 'cursor-1',
                has_more: true,
              }
            : page2
          : firstPage,
    )

    const queryClient = createTestQueryClient()
    const hook = renderHook(
      () => ({
        feed: useSignalFeedQuery(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS),
        loadMore: useLoadMoreSignalFeed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS),
      }),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )
    await waitFor(() => expect(hook.result.current.feed.isSuccess).toBe(true))

    act(() => hook.result.current.loadMore.mutate())

    await waitFor(() => expect(hook.result.current.loadMore.isStalled).toBe(true))
    expect(hook.result.current.loadMore.isError).toBe(false)
    let data = queryClient.getQueryData<SignalFeedCacheState>(
      signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS),
    )
    expect(readSignalFeedCache(data!).items.map((item) => item.id)).toEqual(page1Ids)
    expect(data?.readingWindow.stalled).toBe(true)

    act(() => hook.result.current.loadMore.retryStalledContinuation())

    await waitFor(() => expect(hook.result.current.loadMore.isStalled).toBe(false))
    data = queryClient.getQueryData<SignalFeedCacheState>(
      signalsQueryKeys.feed(EST, 'personal', EMPTY_SIGNAL_FEED_FILTERS),
    )
    expect(readSignalFeedCache(data!).items.map((item) => item.id)).toEqual([
      ...page1Ids,
      ...page2Ids,
    ])
  })
})

describe('useRefreshSignalFeed', () => {
  beforeEach(() => {
    fetchSignalFeed.mockReset()
  })

  it('writes the response under the query key captured when refresh starts', async () => {
    let resolveRefresh: ((page: SignalFeedResponse) => void) | undefined
    fetchSignalFeed.mockImplementation(
      () =>
        new Promise<SignalFeedResponse>((resolve) => {
          resolveRefresh = resolve
        }),
    )
    const queryClient = createTestQueryClient()
    const openFilters = { ...EMPTY_SIGNAL_FEED_FILTERS, statuses: ['open'] as const }
    const interestingFilters = {
      ...EMPTY_SIGNAL_FEED_FILTERS,
      statuses: ['interesting'] as const,
    }
    const hook = renderHook(
      ({ filters }) => useRefreshSignalFeed(EST, 'personal', filters),
      {
        initialProps: { filters: openFilters },
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    act(() => {
      hook.result.current.mutate()
    })
    await waitFor(() => expect(fetchSignalFeed).toHaveBeenCalledTimes(1))
    hook.rerender({ filters: interestingFilters })
    await act(async () => {
      resolveRefresh?.({
        ...firstPage,
        items: [buildFeedItem({ id: 'open-refresh' })],
      })
    })

    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true))
    expect(
      readSignalFeedCache(
        queryClient.getQueryData<SignalFeedCacheState>(
          signalsQueryKeys.feed(EST, 'personal', openFilters),
        )!,
      ).items.map((item) => item.id),
    ).toEqual(['open-refresh'])
    expect(
      queryClient.getQueryData(
        signalsQueryKeys.feed(EST, 'personal', interestingFilters),
      ),
    ).toBeUndefined()
  })
})
