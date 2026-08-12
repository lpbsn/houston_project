// @vitest-environment jsdom

import { QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

const fetchAnalyticsDashboardMock = vi.fn()

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    fetchAnalyticsDashboard: (...args: unknown[]) => fetchAnalyticsDashboardMock(...args),
  }
})

import { analyticsQueryKeys } from './api'
import { useAnalyticsDashboardQuery } from './hooks'
import type { AnalyticsUrlState } from './lib/analytics-url-state'

const state: AnalyticsUrlState = {
  periodStart: '2026-07-13T10:30:00.000Z',
  periodEnd: '2026-08-12T10:30:00.000Z',
  organizationId: null,
}

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = createTestQueryClient()
  return createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useAnalyticsDashboardQuery', () => {
  afterEach(() => {
    fetchAnalyticsDashboardMock.mockReset()
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
