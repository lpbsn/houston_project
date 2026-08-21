// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { createMemoryHistory, type AppHistory } from '@/app/app-history'
import { AppRouteProvider } from '@/app/app-routes'
import type { AnalyticsDashboardResponse } from '@/features/analytics/api'
import { AnalyticsApiError } from '@/features/analytics/api'
import { AnalyticsPage } from '@/features/analytics/pages/analytics-page'

const dashboardQueryMock = vi.fn()

const { authState } = vi.hoisted(() => ({
  authState: {
    current: {
      bootstrap: null as unknown,
      isBootstrapping: false,
      isReady: true,
    },
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/features/analytics/hooks', () => ({
  useAnalyticsDashboardQuery: (...args: unknown[]) => dashboardQueryMock(...args),
}))

function comparison(
  currentValue: number | null,
  coverage: AnalyticsDashboardResponse['operational_resolution_rate']['coverage'] = 'complete',
  relativeChange: number | null = 0.1,
) {
  return {
    current_value: currentValue,
    previous_value: 1,
    absolute_delta: 1,
    relative_change: relativeChange,
    relative_change_status: coverage === 'complete' ? 'computed' : 'not_applicable',
    coverage,
  }
}

function dashboard(
  overrides: Partial<AnalyticsDashboardResponse> = {},
): AnalyticsDashboardResponse {
  return {
    period_days: 7,
    current_period: {
      period_start: '2026-08-14T12:00:00.000Z',
      period_end: '2026-08-21T12:00:00.000Z',
    },
    previous_period: {
      period_start: '2026-08-07T12:00:00.000Z',
      period_end: '2026-08-14T12:00:00.000Z',
    },
    history_reliable_from: '2026-01-01T00:00:00.000Z',
    scope_type: 'cross',
    establishment_id: null,
    establishment_ids: ['est-1'],
    recurring_patterns: [
      {
        pattern_id: '11111111-1111-4111-8111-111111111111',
        name: 'Chaîne du froid',
        signal_count: 18,
        comparison: comparison(18),
      },
    ],
    new_patterns: [
      {
        pattern_id: '22222222-2222-4222-8222-222222222222',
        name: 'Rangement terrasse',
        first_seen_at: '2026-08-17T12:00:00.000Z',
        observation_count: 4,
        establishment_count: 1,
        establishment_id: 'est-1',
        establishment_name: 'Nord',
      },
      {
        pattern_id: '22222222-2222-4222-8222-222222222223',
        name: 'Bruit extraction',
        first_seen_at: '2026-08-13T12:00:00.000Z',
        observation_count: 2,
        establishment_count: 1,
        establishment_id: 'est-1',
        establishment_name: 'Nord',
      },
      {
        pattern_id: '22222222-2222-4222-8222-222222222224',
        name: 'Chariots',
        first_seen_at: '2026-08-10T12:00:00.000Z',
        observation_count: 1,
        establishment_count: 1,
        establishment_id: 'est-1',
        establishment_name: 'Nord',
      },
      {
        pattern_id: '22222222-2222-4222-8222-222222222225',
        name: 'Motif 4',
        first_seen_at: '2026-08-16T12:00:00.000Z',
        observation_count: 1,
        establishment_count: 1,
        establishment_id: 'est-1',
        establishment_name: 'Nord',
      },
      {
        pattern_id: '22222222-2222-4222-8222-222222222226',
        name: 'Motif 5',
        first_seen_at: '2026-08-16T12:00:00.000Z',
        observation_count: 1,
        establishment_count: 1,
        establishment_id: 'est-1',
        establishment_name: 'Nord',
      },
      {
        pattern_id: '22222222-2222-4222-8222-222222222227',
        name: 'Motif 6 caché',
        first_seen_at: '2026-08-16T12:00:00.000Z',
        observation_count: 1,
        establishment_count: 1,
        establishment_id: 'est-1',
        establishment_name: 'Nord',
      },
    ],
    new_patterns_preview_limit: 5,
    contributors: [
      {
        user_id: '33333333-3333-4333-8333-333333333333',
        name: 'Nadia B.',
        pts: 24,
        roles: ['staff'],
        poles: ['Cuisine'],
      },
    ],
    observation_delay_canceled: {
      median_seconds: 86400,
      mean_seconds: 90000,
      p90_seconds: null,
      n: 3,
      comparison: comparison(86400, 'complete', -0.06),
    },
    observation_delay_resolved: {
      median_seconds: 200000,
      mean_seconds: 210000,
      p90_seconds: null,
      n: 4,
      comparison: comparison(200000),
    },
    observation_delay_transformed: {
      median_seconds: 100000,
      mean_seconds: 110000,
      p90_seconds: null,
      n: 2,
      comparison: comparison(100000),
    },
    operational_resolution_rate: comparison(0.75, 'complete', 0.05),
    closure_resolved_share: comparison(0.8),
    reopenings: comparison(2, 'complete', 0),
    open_observation_count: 12,
    aging_buckets: [
      { key: 'lt_3d', label: '< 3 j', count: 4, share: 0.33 },
      { key: 'gt_15d', label: '> 15 j', count: 2, share: 0.16 },
    ],
    aging_over_15d_share: comparison(0.16, 'partial', null),
    plan_delay_canceled: {
      median_seconds: 86400,
      mean_seconds: 86400,
      p90_seconds: null,
      n: 1,
      comparison: comparison(86400),
    },
    plan_delay_resolved: {
      median_seconds: 200000,
      mean_seconds: 200000,
      p90_seconds: null,
      n: 2,
      comparison: comparison(200000),
    },
    plan_validation: {
      median_seconds: 50000,
      mean_seconds: 50000,
      p90_seconds: null,
      n: 2,
      comparison: comparison(50000),
    },
    plan_deadlines: {
      early: 0.21,
      on_time: 0.54,
      late: 0.25,
      n: 10,
      early_comparison: comparison(0.21),
      on_time_comparison: comparison(0.54),
      late_comparison: comparison(0.25),
    },
    zones: [],
    zones_preview_limit: 7,
    poles: [],
    ...overrides,
  }
}

function managerBootstrap() {
  return {
    memberships: [
      {
        id: 'member-1',
        establishment_id: 'est-1',
        establishment_name: 'Nord',
        organization_id: 'org-1',
        organization_name: 'Spore',
        role: 'manager',
        status: 'active',
        scopes: [],
        scope_summary: { business_unit_count: 0 },
      },
    ],
    active_membership: {
      id: 'member-1',
      establishment_id: 'est-1',
      role: 'manager',
      status: 'active',
    },
  }
}

function renderAnalyticsPage(href = '/cross'): AppHistory {
  const history = createMemoryHistory(href)
  render(createElement(AppRouteProvider, { history }, createElement(AnalyticsPage, { scope: { type: 'cross' } })))
  return history
}

afterEach(() => {
  cleanup()
  dashboardQueryMock.mockReset()
})

describe('AnalyticsPage', () => {
  it('refuses staff without fetching the dashboard', () => {
    authState.current.bootstrap = {
      memberships: [{ role: 'staff', status: 'active', establishment_id: 'est-1' }],
    }
    dashboardQueryMock.mockReturnValue({ isLoading: false, isError: false, data: undefined })

    renderAnalyticsPage()

    expect(screen.getByText('Accès refusé')).toBeTruthy()
    expect(dashboardQueryMock.mock.calls[0]?.[1]).toEqual({ enabled: false })
  })

  it('writes period=15d in the URL', () => {
    authState.current.bootstrap = managerBootstrap()
    dashboardQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: dashboard(),
      refetch: vi.fn(),
    })

    const history = renderAnalyticsPage('/cross?period=7d')
    fireEvent.click(screen.getByRole('button', { name: '15 j' }))
    expect(history.getHref()).toBe('/cross?period=15d')
  })

  it('hides percent deltas when coverage is not complete', () => {
    authState.current.bootstrap = managerBootstrap()
    dashboardQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: dashboard(),
      refetch: vi.fn(),
    })

    renderAnalyticsPage()
    expect(screen.getByText('Données incomplètes')).toBeTruthy()
    expect(screen.queryByText('Motif 6 caché')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Voir tout' }))
    expect(screen.getByText('Motif 6 caché')).toBeTruthy()
  })

  it('shows explicit 403 copy', () => {
    authState.current.bootstrap = managerBootstrap()
    dashboardQueryMock.mockReturnValue({
      isLoading: false,
      isError: true,
      error: new AnalyticsApiError({ status: 403, detail: 'nope' }),
      refetch: vi.fn(),
    })

    renderAnalyticsPage()
    expect(screen.getByText('Vous n’avez pas accès à cet établissement.')).toBeTruthy()
  })

  it('shows IA and export placeholders', () => {
    authState.current.bootstrap = managerBootstrap()
    dashboardQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: dashboard(),
      refetch: vi.fn(),
    })

    renderAnalyticsPage()
    expect(screen.getByText('Résumé de la semaine')).toBeTruthy()
    expect(screen.getAllByText('Bientôt disponible').length).toBeGreaterThan(0)
    expect(screen.getByText('CA vs Observations')).toBeTruthy()
  })
})
