// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { useHistoryList } from './hooks'

const fetchSignalHistory = vi.fn()

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    fetchSignalHistory: (...args: unknown[]) => fetchSignalHistory(...args),
  }
})

function page(id: string, nextCursor: string | null, hasMore: boolean) {
  return {
    items: [
      {
        id,
        title: id,
        status: 'resolved',
        terminal_at: '2026-09-28T10:00:00Z',
        terminal_date_source: 'field',
        termination_origin: 'manual',
        termination_actor_display_name: null,
        establishment_id: 'est-1',
        establishment_name: 'Paris',
      },
    ],
    next_cursor: nextCursor,
    has_more: hasMore,
    undated_count: 0,
  }
}

describe('useHistoryList', () => {
  beforeEach(() => {
    fetchSignalHistory.mockReset()
  })

  it('refreshes from page one and abandons loaded continuations', async () => {
    fetchSignalHistory
      .mockResolvedValueOnce(page('first', 'cursor-2', true))
      .mockResolvedValueOnce(page('second', null, false))
      .mockResolvedValueOnce(page('fresh', null, false))
    const queryClient = createTestQueryClient()
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children)
    const { result } = renderHook(
      () =>
        useHistoryList({
          source: 'establishment',
          establishmentId: 'est-1',
          kind: 'signals',
          viewMode: 'personal',
          period: '30',
          status: 'all',
        }),
      { wrapper },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    await act(async () => {
      await result.current.fetchNextPage()
    })
    await waitFor(() => expect(result.current.data?.pages).toHaveLength(2))

    await act(async () => {
      await result.current.refresh()
    })
    await waitFor(() =>
      expect(result.current.data?.pages.map((current) => current.items[0]?.id)).toEqual(['fresh']),
    )
    expect(fetchSignalHistory.mock.calls[2]?.[1]).toHaveProperty('cursor', undefined)
  })
})
