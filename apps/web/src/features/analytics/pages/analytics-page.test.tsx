// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AnalyticsDashboardResponse } from '@/features/analytics/api'
import { AnalyticsApiError } from '@/features/analytics/api'
import { AnalyticsPage } from '@/features/analytics/pages/analytics-page'

const dashboardQueryMock = vi.fn()
const refetchMock = vi.fn()

const { authState } = vi.hoisted(() => ({
  authState: {
    current: {
      bootstrap: null,
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

function bootstrap(roles: string | string[]) {
  const roleList = Array.isArray(roles) ? roles : [roles]
  return {
    memberships: roleList.map((role, index) => ({
      id: `member-${role}-${index}`,
      establishment_id: `est-${index}`,
      establishment_name: `Spore ${index}`,
      organization_id: `org-${index}`,
      organization_name: 'Spore',
      role,
      status: 'active',
      scopes: [],
      scope_summary: { business_unit_count: 0 },
    })),
  }
}

function comparison(
  currentValue: number | null,
  overrides: Partial<AnalyticsDashboardResponse['signals_analyzed_count']> = {},
): AnalyticsDashboardResponse['signals_analyzed_count'] {
  return {
    current_value: currentValue,
    previous_value: 4,
    absolute_delta: 999,
    relative_change: 0.125,
    relative_change_status: 'computed',
    ...overrides,
  }
}

function kpis(
  overrides: Partial<AnalyticsDashboardResponse['current_kpis']> = {},
): AnalyticsDashboardResponse['current_kpis'] {
  return {
    analytics_signal_population_count: 12,
    signals_analyzed_count: 8,
    operational_patterns_count: 3,
    actionable_signals_count: 2,
    median_resolution_seconds: 7200,
    resolution_time_signal_count: 5,
    invalid_resolution_duration_count: 1,
    business_assignment_coverage: {
      total_count: 12,
      with_pattern_count: 8,
      without_pattern_count: 4,
      coverage_rate: 0.666666,
    },
    technical_classification_state: {
      total_count: 12,
      technical_state_breakdown: {
        missing_assignment: 2,
        processing: 3,
        succeeded: 7,
      },
      technical_terminal_success_count: 7,
      technical_pending_or_error_count: 5,
    },
    recurring_patterns_count: 1,
    recurrence_window: {
      window_start: '2026-07-13T10:30:00.000Z',
      window_end: '2026-08-12T10:30:00.000Z',
    },
    recurrence_status: 'computed',
    ...overrides,
  }
}

function dashboard(
  overrides: Partial<AnalyticsDashboardResponse> = {},
): AnalyticsDashboardResponse {
  return {
    current_period: {
      period_start: '2026-07-13T10:30:00.000Z',
      period_end: '2026-08-12T10:30:00.000Z',
    },
    previous_period: {
      period_start: '2026-06-13T10:30:00.000Z',
      period_end: '2026-07-13T10:30:00.000Z',
    },
    current_kpis: kpis(),
    previous_kpis: kpis(),
    signals_analyzed_count: comparison(8),
    operational_patterns_count: comparison(3, { absolute_delta: -2, relative_change: -0.4 }),
    actionable_signals_count: comparison(2, {
      previous_value: 0,
      absolute_delta: 2,
      relative_change: null,
      relative_change_status: 'undefined_previous_zero',
    }),
    median_resolution_seconds: comparison(7200, {
      absolute_delta: 3600,
      relative_change: 1,
    }),
    recurring_patterns_count: comparison(1),
    recurrence_status: 'computed',
    ...overrides,
  }
}

function setDashboardQuery(value: ReturnType<typeof dashboardQueryMock>) {
  dashboardQueryMock.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: refetchMock,
    ...value,
  })
}

describe('AnalyticsPage', () => {
  afterEach(() => {
    cleanup()
    dashboardQueryMock.mockReset()
    refetchMock.mockReset()
    window.history.replaceState(null, '', '/')
    authState.current = {
      bootstrap: null,
      isBootstrapping: false,
      isReady: true,
    }
  })

  it('does not enable the dashboard query for Staff-only users', () => {
    setDashboardQuery({})
    authState.current = {
      bootstrap: bootstrap('staff'),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(
      screen.getByText('Analytics est disponible pour les propriétaires, directeurs et managers.'),
    ).toBeTruthy()
    expect(dashboardQueryMock).toHaveBeenCalledWith(
      expect.any(Object),
      expect.objectContaining({ enabled: false }),
    )
  })

  it('enables the dashboard for Analytics memberships, including multi-membership users', () => {
    setDashboardQuery({ data: dashboard() })
    authState.current = {
      bootstrap: bootstrap(['staff', 'manager']),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(screen.getByText('Dashboard Analytics')).toBeTruthy()
    expect(dashboardQueryMock).toHaveBeenCalledWith(
      expect.objectContaining({
        periodStart: expect.any(String),
        periodEnd: expect.any(String),
        organizationId: null,
      }),
      expect.objectContaining({ enabled: true }),
    )
  })

  it('renders a loading state while the dashboard query is pending', () => {
    setDashboardQuery({ isLoading: true })
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(screen.getByRole('status', { name: 'Chargement Analytics' })).toBeTruthy()
  })

  it('renders an error state with retry', () => {
    setDashboardQuery({
      isError: true,
      error: new AnalyticsApiError({
        status: 400,
        detail: 'Période invalide.',
        code: 'analytics_period_invalid',
      }),
    })
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(screen.getByText('Période invalide.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(refetchMock).toHaveBeenCalled()
  })

  it('renders dashboard KPI values from API comparison objects without recomputing deltas', () => {
    setDashboardQuery({ data: dashboard() })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(screen.getByText('Signals analysés')).toBeTruthy()
    expect(screen.getAllByText('8').length).toBeGreaterThan(0)
    expect(screen.getAllByText('+999').length).toBeGreaterThan(0)
    expect(screen.getByText('-2')).toBeTruthy()
    expect(screen.getAllByText(/12,5\s?%\s+vs précédent/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('non comparable').length).toBeGreaterThan(0)
    expect(screen.getByText('2 h')).toBeTruthy()
  })

  it('renders backend classification coverage and technical breakdowns factually', () => {
    setDashboardQuery({ data: dashboard() })
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(screen.getByText('Traitement Analytics')).toBeTruthy()
    expect(screen.getByText('Population')).toBeTruthy()
    expect(screen.getByText('Avec motif')).toBeTruthy()
    expect(screen.getByText('Sans motif')).toBeTruthy()
    expect(screen.getByText('66,7 %')).toBeTruthy()
    expect(screen.getByText('Sans assignment')).toBeTruthy()
    expect(screen.getByText('En traitement')).toBeTruthy()
    expect(screen.getByText('Succès terminaux 7')).toBeTruthy()
    expect(screen.getByText('Attente ou erreur 5')).toBeTruthy()
  })

  it('renders an empty state when the backend population is zero', () => {
    setDashboardQuery({
      data: dashboard({
        current_kpis: kpis({
          analytics_signal_population_count: 0,
          business_assignment_coverage: {
            total_count: 0,
            with_pattern_count: 0,
            without_pattern_count: 0,
            coverage_rate: null,
          },
          technical_classification_state: {
            total_count: 0,
            technical_state_breakdown: {},
            technical_terminal_success_count: 0,
            technical_pending_or_error_count: 0,
          },
        }),
      }),
    })
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(screen.getByText('Aucune donnée Analytics visible')).toBeTruthy()
  })

  it('does not crash when Analytics query params are invalid', () => {
    window.history.replaceState(
      null,
      '',
      '/analytics?period_start=2026-13-01T00%3A00%3A00Z&establishment_id=ignored',
    )
    setDashboardQuery({ data: dashboard() })
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(screen.getByText('Dashboard Analytics')).toBeTruthy()
    expect(dashboardQueryMock).toHaveBeenCalledWith(
      expect.objectContaining({ organizationId: null }),
      expect.objectContaining({ enabled: true }),
    )
  })
})
