// @vitest-environment jsdom

import { QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

const fetchAnalyticsDashboardMock = vi.fn()
const fetchAnalyticsPatternDetailMock = vi.fn()
const reportAnalyticsPatternIssueMock = vi.fn()
const fetchAnalyticsPatternsMock = vi.fn()
const fetchAnalyticsPatternSignalsMock = vi.fn()

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    fetchAnalyticsDashboard: (...args: unknown[]) => fetchAnalyticsDashboardMock(...args),
    fetchAnalyticsPatternDetail: (...args: unknown[]) => fetchAnalyticsPatternDetailMock(...args),
    fetchAnalyticsPatternSignals: (...args: unknown[]) =>
      fetchAnalyticsPatternSignalsMock(...args),
    fetchAnalyticsPatterns: (...args: unknown[]) => fetchAnalyticsPatternsMock(...args),
    reportAnalyticsPatternIssue: (...args: unknown[]) =>
      reportAnalyticsPatternIssueMock(...args),
  }
})

import { analyticsQueryKeys } from './api'
import {
  useAnalyticsDashboardQuery,
  useAnalyticsPatternDetailQuery,
  useAnalyticsPatternSignalsInfiniteQuery,
  useAnalyticsPatternsInfiniteQuery,
  useReportAnalyticsPatternIssueMutation,
} from './hooks'
import type { AnalyticsUrlState } from './lib/analytics-url-state'

const state: AnalyticsUrlState = {
  periodStart: '2026-07-13T10:30:00.000Z',
  periodEnd: '2026-08-12T10:30:00.000Z',
  organizationId: null,
  establishmentIds: [],
  q: '',
  recurrence: 'all',
  responsibleBusinessUnitIds: [],
  responsibleBusinessUnitUnassigned: false,
  signalStatuses: [],
}

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = createTestQueryClient()
  return createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useAnalyticsDashboardQuery', () => {
  afterEach(() => {
    fetchAnalyticsDashboardMock.mockReset()
    fetchAnalyticsPatternDetailMock.mockReset()
    reportAnalyticsPatternIssueMock.mockReset()
    fetchAnalyticsPatternsMock.mockReset()
    fetchAnalyticsPatternSignalsMock.mockReset()
  })

  it('fetches the dashboard with the resolved URL state', async () => {
    fetchAnalyticsDashboardMock.mockResolvedValue({ current_kpis: {} })

    const { result } = renderHook(() => useAnalyticsDashboardQuery(state), { wrapper })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(fetchAnalyticsDashboardMock).toHaveBeenCalledWith(state)
  })

  it('does not fetch when disabled', () => {
    renderHook(() => useAnalyticsDashboardQuery(state, { enabled: false }), { wrapper })

    expect(fetchAnalyticsDashboardMock).not.toHaveBeenCalled()
  })

  it('uses a stable query key derived from period and organization', () => {
    expect(analyticsQueryKeys.dashboard(state)).toEqual([
      'analytics',
      'dashboard',
      {
        periodStart: '2026-07-13T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
        organizationId: null,
      },
    ])
  })

  it('fetches a new dashboard when the search-derived state changes', async () => {
    fetchAnalyticsDashboardMock.mockResolvedValue({ current_kpis: {} })
    const nextState = {
      ...state,
      organizationId: '11111111-1111-4111-8111-111111111111',
    }

    const { rerender } = renderHook(
      ({ currentState }) => useAnalyticsDashboardQuery(currentState),
      {
        initialProps: { currentState: state },
        wrapper,
      },
    )

    await waitFor(() => {
      expect(fetchAnalyticsDashboardMock).toHaveBeenCalledWith(state)
    })

    rerender({ currentState: nextState })

    await waitFor(() => {
      expect(fetchAnalyticsDashboardMock).toHaveBeenCalledWith(nextState)
    })
  })
})

describe('useAnalyticsPatternDetailQuery', () => {
  afterEach(() => {
    fetchAnalyticsPatternDetailMock.mockReset()
    fetchAnalyticsPatternSignalsMock.mockReset()
  })

  it('fetches pattern detail with the resolved URL state', async () => {
    fetchAnalyticsPatternDetailMock.mockResolvedValue({ identity: { label: 'Retard' } })

    const { result } = renderHook(
      () => useAnalyticsPatternDetailQuery('pattern-1', state),
      { wrapper },
    )

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(fetchAnalyticsPatternDetailMock).toHaveBeenCalledWith('pattern-1', state)
  })

  it('does not fetch pattern detail when disabled', () => {
    renderHook(() => useAnalyticsPatternDetailQuery('pattern-1', state, { enabled: false }), {
      wrapper,
    })

    expect(fetchAnalyticsPatternDetailMock).not.toHaveBeenCalled()
  })

  it('keys pattern detail only by pattern, period, and organization', () => {
    expect(
      analyticsQueryKeys.patternDetail('pattern-1', {
        ...state,
        q: 'ignored',
        recurrence: 'recurrent',
        establishmentIds: ['22222222-2222-4222-8222-222222222222'],
      }),
    ).toEqual([
      'analytics',
      'pattern-detail',
      'pattern-1',
      {
        periodStart: '2026-07-13T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
        organizationId: null,
      },
    ])
  })
})

describe('useAnalyticsPatternSignalsInfiniteQuery', () => {
  afterEach(() => {
    fetchAnalyticsPatternSignalsMock.mockReset()
  })

  it('uses backend cursors as page params and keys only supported dimensions', async () => {
    fetchAnalyticsPatternSignalsMock
      .mockResolvedValueOnce({
        items: [],
        has_more: true,
        next_cursor: 'cursor-1',
      })
      .mockResolvedValueOnce({
        items: [],
        has_more: false,
        next_cursor: null,
      })
    const filteredState: AnalyticsUrlState = {
      ...state,
      q: 'ignored',
      recurrence: 'recurrent',
      establishmentIds: ['22222222-2222-4222-8222-222222222222'],
    }

    const { result } = renderHook(
      () =>
        useAnalyticsPatternSignalsInfiniteQuery('pattern-1', filteredState, {
          pageSize: 25,
        }),
      { wrapper },
    )

    await waitFor(() => {
      expect(result.current.hasNextPage).toBe(true)
    })

    await result.current.fetchNextPage()

    expect(fetchAnalyticsPatternSignalsMock).toHaveBeenNthCalledWith(1, 'pattern-1', filteredState, {
      cursor: undefined,
      pageSize: 25,
    })
    expect(fetchAnalyticsPatternSignalsMock).toHaveBeenNthCalledWith(2, 'pattern-1', filteredState, {
      cursor: 'cursor-1',
      pageSize: 25,
    })
    expect(analyticsQueryKeys.patternSignals('pattern-1', filteredState, 25)).toEqual([
      'analytics',
      'pattern-signals',
      'pattern-1',
      {
        periodStart: '2026-07-13T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
        organizationId: null,
        pageSize: 25,
      },
    ])
  })

  it('does not fetch pattern signals when disabled', () => {
    renderHook(
      () => useAnalyticsPatternSignalsInfiniteQuery('pattern-1', state, { enabled: false }),
      { wrapper },
    )

    expect(fetchAnalyticsPatternSignalsMock).not.toHaveBeenCalled()
  })
})

describe('useAnalyticsPatternsInfiniteQuery', () => {
  afterEach(() => {
    fetchAnalyticsPatternsMock.mockReset()
  })

  it('uses backend cursors as page params and keeps filters in the query key', async () => {
    fetchAnalyticsPatternsMock
      .mockResolvedValueOnce({
        items: [],
        has_more: true,
        next_cursor: 'cursor-1',
      })
      .mockResolvedValueOnce({
        items: [],
        has_more: false,
        next_cursor: null,
      })
    const filteredState: AnalyticsUrlState = {
      ...state,
      q: 'retard',
      recurrence: 'recurrent',
      establishmentIds: ['22222222-2222-4222-8222-222222222222'],
    }

    const { result } = renderHook(
      () => useAnalyticsPatternsInfiniteQuery(filteredState, { pageSize: 25 }),
      { wrapper },
    )

    await waitFor(() => {
      expect(result.current.hasNextPage).toBe(true)
    })

    await result.current.fetchNextPage()

    expect(fetchAnalyticsPatternsMock).toHaveBeenNthCalledWith(1, filteredState, {
      cursor: undefined,
      pageSize: 25,
    })
    expect(fetchAnalyticsPatternsMock).toHaveBeenNthCalledWith(2, filteredState, {
      cursor: 'cursor-1',
      pageSize: 25,
    })
    expect(analyticsQueryKeys.patterns(filteredState, 25)).toEqual([
      'analytics',
      'patterns',
      expect.objectContaining({
        q: 'retard',
        recurrence: 'recurrent',
        establishmentIds: ['22222222-2222-4222-8222-222222222222'],
        pageSize: 25,
      }),
    ])
  })
})

describe('useReportAnalyticsPatternIssueMutation', () => {
  afterEach(() => {
    reportAnalyticsPatternIssueMock.mockReset()
  })

  it('posts reports without automatic retry', async () => {
    reportAnalyticsPatternIssueMock.mockRejectedValue(new Error('network timeout'))

    const { result } = renderHook(() => useReportAnalyticsPatternIssueMutation(), {
      wrapper,
    })

    await expect(
      result.current.mutateAsync({
        patternId: 'pattern-1',
        signalId: 'signal-1',
        body: {
          reason: 'wrong_pattern',
          comment: 'Mauvais motif',
        },
      }),
    ).rejects.toThrow('network timeout')

    expect(reportAnalyticsPatternIssueMock).toHaveBeenCalledTimes(1)
  })
})
