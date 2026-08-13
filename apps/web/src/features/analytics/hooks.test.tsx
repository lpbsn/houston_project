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
const fetchAnalyticsPatternGovernanceTargetsMock = vi.fn()
const renameAnalyticsPatternMock = vi.fn()
const mergeAnalyticsPatternsMock = vi.fn()
const moveAnalyticsPatternSignalsMock = vi.fn()
const splitAnalyticsPatternToExistingMock = vi.fn()
const splitAnalyticsPatternToNewMock = vi.fn()

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    fetchAnalyticsDashboard: (...args: unknown[]) => fetchAnalyticsDashboardMock(...args),
    fetchAnalyticsPatternDetail: (...args: unknown[]) => fetchAnalyticsPatternDetailMock(...args),
    fetchAnalyticsPatternSignals: (...args: unknown[]) =>
      fetchAnalyticsPatternSignalsMock(...args),
    fetchAnalyticsPatternGovernanceTargets: (...args: unknown[]) =>
      fetchAnalyticsPatternGovernanceTargetsMock(...args),
    fetchAnalyticsPatterns: (...args: unknown[]) => fetchAnalyticsPatternsMock(...args),
    renameAnalyticsPattern: (...args: unknown[]) => renameAnalyticsPatternMock(...args),
    mergeAnalyticsPatterns: (...args: unknown[]) => mergeAnalyticsPatternsMock(...args),
    moveAnalyticsPatternSignals: (...args: unknown[]) =>
      moveAnalyticsPatternSignalsMock(...args),
    splitAnalyticsPatternToExisting: (...args: unknown[]) =>
      splitAnalyticsPatternToExistingMock(...args),
    splitAnalyticsPatternToNew: (...args: unknown[]) =>
      splitAnalyticsPatternToNewMock(...args),
    reportAnalyticsPatternIssue: (...args: unknown[]) =>
      reportAnalyticsPatternIssueMock(...args),
  }
})

import { analyticsQueryKeys } from './api'
import {
  useAnalyticsDashboardQuery,
  useAnalyticsPatternGovernanceTargetsInfiniteQuery,
  useAnalyticsPatternDetailQuery,
  useAnalyticsPatternSignalsInfiniteQuery,
  useAnalyticsPatternsInfiniteQuery,
  useMergeAnalyticsPatternsMutation,
  useMoveAnalyticsPatternSignalsMutation,
  useRenameAnalyticsPatternMutation,
  useReportAnalyticsPatternIssueMutation,
  useSplitAnalyticsPatternToExistingMutation,
  useSplitAnalyticsPatternToNewMutation,
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
    fetchAnalyticsPatternGovernanceTargetsMock.mockReset()
    renameAnalyticsPatternMock.mockReset()
    mergeAnalyticsPatternsMock.mockReset()
    moveAnalyticsPatternSignalsMock.mockReset()
    splitAnalyticsPatternToExistingMock.mockReset()
    splitAnalyticsPatternToNewMock.mockReset()
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

describe('useAnalyticsPatternGovernanceTargetsInfiniteQuery', () => {
  afterEach(() => {
    fetchAnalyticsPatternGovernanceTargetsMock.mockReset()
  })

  it('uses backend cursors as page params and keys search/page size only', async () => {
    fetchAnalyticsPatternGovernanceTargetsMock
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

    const { result } = renderHook(
      () =>
        useAnalyticsPatternGovernanceTargetsInfiniteQuery('pattern-1', {
          q: 'retard',
          pageSize: 20,
        }),
      { wrapper },
    )

    await waitFor(() => {
      expect(result.current.hasNextPage).toBe(true)
    })

    await result.current.fetchNextPage()

    expect(fetchAnalyticsPatternGovernanceTargetsMock).toHaveBeenNthCalledWith(1, 'pattern-1', {
      cursor: undefined,
      pageSize: 20,
      q: 'retard',
    })
    expect(fetchAnalyticsPatternGovernanceTargetsMock).toHaveBeenNthCalledWith(2, 'pattern-1', {
      cursor: 'cursor-1',
      pageSize: 20,
      q: 'retard',
    })
    expect(
      analyticsQueryKeys.governanceTargets('pattern-1', {
        q: 'retard',
        pageSize: 20,
      }),
    ).toEqual([
      'analytics',
      'governance-targets',
      'pattern-1',
      {
        q: 'retard',
        pageSize: 20,
      },
    ])
  })

  it('does not fetch governance targets when disabled', () => {
    renderHook(
      () =>
        useAnalyticsPatternGovernanceTargetsInfiniteQuery('pattern-1', {
          enabled: false,
        }),
      { wrapper },
    )

    expect(fetchAnalyticsPatternGovernanceTargetsMock).not.toHaveBeenCalled()
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

describe('owner governance mutations', () => {
  afterEach(() => {
    renameAnalyticsPatternMock.mockReset()
    mergeAnalyticsPatternsMock.mockReset()
    moveAnalyticsPatternSignalsMock.mockReset()
    splitAnalyticsPatternToExistingMock.mockReset()
    splitAnalyticsPatternToNewMock.mockReset()
  })

  it('disables automatic retry for owner governance POSTs', async () => {
    renameAnalyticsPatternMock.mockRejectedValue(new Error('network timeout'))
    mergeAnalyticsPatternsMock.mockRejectedValue(new Error('network timeout'))
    moveAnalyticsPatternSignalsMock.mockRejectedValue(new Error('network timeout'))
    splitAnalyticsPatternToExistingMock.mockRejectedValue(new Error('network timeout'))
    splitAnalyticsPatternToNewMock.mockRejectedValue(new Error('network timeout'))

    const { result: rename } = renderHook(() => useRenameAnalyticsPatternMutation(), {
      wrapper,
    })
    const { result: merge } = renderHook(() => useMergeAnalyticsPatternsMutation(), {
      wrapper,
    })
    const { result: move } = renderHook(() => useMoveAnalyticsPatternSignalsMutation(), {
      wrapper,
    })
    const { result: splitExisting } = renderHook(
      () => useSplitAnalyticsPatternToExistingMutation(),
      { wrapper },
    )
    const { result: splitNew } = renderHook(
      () => useSplitAnalyticsPatternToNewMutation(),
      { wrapper },
    )

    await expect(
      rename.current.mutateAsync({
        patternId: 'pattern-1',
        body: { label: 'New' },
      }),
    ).rejects.toThrow('network timeout')
    await expect(
      merge.current.mutateAsync({
        patternId: 'pattern-1',
        body: { target_pattern_id: 'pattern-2' },
      }),
    ).rejects.toThrow('network timeout')
    await expect(
      move.current.mutateAsync({
        patternId: 'pattern-1',
        body: { target_pattern_id: 'pattern-2', signal_ids: ['signal-1'] },
      }),
    ).rejects.toThrow('network timeout')
    await expect(
      splitExisting.current.mutateAsync({
        patternId: 'pattern-1',
        body: { target_pattern_id: 'pattern-2', signal_ids: ['signal-1'] },
      }),
    ).rejects.toThrow('network timeout')
    await expect(
      splitNew.current.mutateAsync({
        patternId: 'pattern-1',
        body: { label: 'Split', signal_ids: ['signal-1'] },
      }),
    ).rejects.toThrow('network timeout')

    expect(renameAnalyticsPatternMock).toHaveBeenCalledTimes(1)
    expect(mergeAnalyticsPatternsMock).toHaveBeenCalledTimes(1)
    expect(moveAnalyticsPatternSignalsMock).toHaveBeenCalledTimes(1)
    expect(splitAnalyticsPatternToExistingMock).toHaveBeenCalledTimes(1)
    expect(splitAnalyticsPatternToNewMock).toHaveBeenCalledTimes(1)
  })
})
