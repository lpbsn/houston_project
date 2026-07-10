// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { signalsQueryKeys } from './api'
import {
  useCancelSignalMutation,
  usePinSignalMutation,
  useResolveSignalMutation,
  useSignalUrgencyMutation,
  useUnpinSignalMutation,
} from './hooks'
import { EMPTY_SIGNAL_FEED_FILTERS } from './lib/signal-feed-filters'

const resolveSignal = vi.fn(async () => ({ id: 'signal-1', status: 'resolved' }))
const cancelSignal = vi.fn(async () => ({ id: 'signal-1', status: 'canceled' }))
const pinSignal = vi.fn(async () => ({
  id: 'signal-1',
  urgency: 'normal',
  is_pinned: true,
}))
const unpinSignal = vi.fn(async () => ({
  id: 'signal-1',
  urgency: 'normal',
  is_pinned: false,
}))
const setSignalUrgency = vi.fn(async () => ({
  id: 'signal-1',
  urgency: 'high',
  is_pinned: false,
}))

const cacheContext = {
  viewMode: 'personal' as const,
  filters: EMPTY_SIGNAL_FEED_FILTERS,
}

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    resolveSignal: (...args: unknown[]) => resolveSignal(...args),
    cancelSignal: (...args: unknown[]) => cancelSignal(...args),
    pinSignal: (...args: unknown[]) => pinSignal(...args),
    unpinSignal: (...args: unknown[]) => unpinSignal(...args),
    setSignalUrgency: (...args: unknown[]) => setSignalUrgency(...args),
  }
})

function renderMutationHook<T>(render: () => T) {
  const queryClient = createTestQueryClient()
  const hook = renderHook(render, {
    wrapper: ({ children }) =>
      createElement(QueryClientProvider, { client: queryClient }, children),
  })
  return { ...hook, queryClient }
}

describe('useResolveSignalMutation', () => {
  beforeEach(() => {
    resolveSignal.mockClear()
  })

  it('invalidates signal queries on success', async () => {
    const { result, queryClient } = renderMutationHook(() =>
      useResolveSignalMutation('est-1'),
    )
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    result.current.mutate('signal-1')

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(resolveSignal).toHaveBeenCalledWith('est-1', 'signal-1')
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: signalsQueryKeys.all })
  })
})

describe('useCancelSignalMutation', () => {
  beforeEach(() => {
    cancelSignal.mockClear()
  })

  it('invalidates signal queries and removes detail cache on success', async () => {
    const { result, queryClient } = renderMutationHook(() =>
      useCancelSignalMutation('est-1'),
    )
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const removeSpy = vi.spyOn(queryClient, 'removeQueries')

    result.current.mutate('signal-1')

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(cancelSignal).toHaveBeenCalledWith('est-1', 'signal-1')
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    expect(removeSpy).toHaveBeenCalledWith({
      queryKey: signalsQueryKeys.detail('est-1', 'signal-1'),
    })
  })
})

describe('usePinSignalMutation', () => {
  beforeEach(() => {
    pinSignal.mockClear()
  })

  it('invalidates feed view modes without establishment-wide detail invalidation', async () => {
    const { result, queryClient } = renderMutationHook(() =>
      usePinSignalMutation('est-1', cacheContext),
    )
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    result.current.mutate('signal-1')

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(pinSignal).toHaveBeenCalledWith('est-1', 'signal-1')
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['signals', 'feed', 'est-1', 'personal'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['signals', 'feed', 'est-1', 'general'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ['signals', 'detail', 'est-1'],
    })
  })
})

describe('useUnpinSignalMutation', () => {
  beforeEach(() => {
    unpinSignal.mockClear()
  })

  it('invalidates feed view modes without establishment-wide detail invalidation', async () => {
    const { result, queryClient } = renderMutationHook(() =>
      useUnpinSignalMutation('est-1', cacheContext),
    )
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    result.current.mutate('signal-1')

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(unpinSignal).toHaveBeenCalledWith('est-1', 'signal-1')
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['signals', 'feed', 'est-1', 'personal'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['signals', 'feed', 'est-1', 'general'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ['signals', 'detail', 'est-1'],
    })
  })
})

describe('useSignalUrgencyMutation', () => {
  beforeEach(() => {
    setSignalUrgency.mockClear()
  })

  it('does not invalidate establishment-wide signal queries on success', async () => {
    const { result, queryClient } = renderMutationHook(() =>
      useSignalUrgencyMutation('est-1', cacheContext),
    )
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const feedKey = signalsQueryKeys.feed('est-1', 'personal', EMPTY_SIGNAL_FEED_FILTERS)

    queryClient.setQueryData(feedKey, {
      pages: [
        {
          items: [
            {
              id: 'signal-1',
              title: 'Fuite',
              structured_summary_short: 'Short',
              status: 'open',
              urgency: 'normal',
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
                can_set_urgency: true,
                can_cancel: false,
                can_resolve: false,
                can_create_linked_action_plan: false,
              },
            },
          ],
          next_cursor: null,
          has_more: false,
          applied_filters: {
            statuses: [],
            business_unit_keys: [],
            activity_subject_ids: [],
          },
        },
      ],
      pageParams: [undefined],
    })

    result.current.mutate({ signalId: 'signal-1', urgency: 'high' })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(setSignalUrgency).toHaveBeenCalledWith('est-1', 'signal-1', 'high')
    expect(invalidateSpy).not.toHaveBeenCalled()
    const data = queryClient.getQueryData<{
      pages: Array<{ items: Array<{ urgency: string }> }>
    }>(feedKey)
    expect(data?.pages[0]?.items[0]?.urgency).toBe('high')
  })
})
