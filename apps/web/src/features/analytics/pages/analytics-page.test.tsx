// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { createBrowserHistory, type AppHistory } from '@/app/app-history'
import { AppRouteProvider } from '@/app/app-routes'
import type { AnalyticsDashboardResponse } from '@/features/analytics/api'
import { AnalyticsApiError } from '@/features/analytics/api'
import { AnalyticsPage } from '@/features/analytics/pages/analytics-page'

const dashboardQueryMock = vi.fn()
const patternsQueryMock = vi.fn()
const filterOptionsQueryMock = vi.fn()
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
  useAnalyticsPatternsInfiniteQuery: (...args: unknown[]) => patternsQueryMock(...args),
  useAnalyticsPatternFilterOptionsQuery: (...args: unknown[]) =>
    filterOptionsQueryMock(...args),
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

function setPatternsQuery(value: ReturnType<typeof patternsQueryMock> = {}) {
  patternsQueryMock.mockReturnValue({
    data: {
      pages: [
        {
          items: [],
          has_more: false,
          next_cursor: null,
        },
      ],
    },
    isLoading: false,
    isError: false,
    error: null,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
    refetch: vi.fn(),
    ...value,
  })
}

function setFilterOptionsQuery(value: ReturnType<typeof filterOptionsQueryMock> = {}) {
  filterOptionsQueryMock.mockReturnValue({
    data: {
      establishments: [],
      responsible_business_units: [],
      includes_unassigned: false,
    },
    isLoading: false,
    isError: false,
    error: null,
    ...value,
  })
}

function renderAnalyticsPage(
  props: { onNavigate?: (pathname: string, options?: { replace?: boolean }) => void } = {},
): AppHistory {
  const history = createBrowserHistory()
  render(createElement(AppRouteProvider, { history }, createElement(AnalyticsPage, props)))
  return history
}

describe('AnalyticsPage', () => {
  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    dashboardQueryMock.mockReset()
    patternsQueryMock.mockReset()
    filterOptionsQueryMock.mockReset()
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
    setPatternsQuery()
    setFilterOptionsQuery()
    authState.current = {
      bootstrap: bootstrap('staff'),
      isBootstrapping: false,
      isReady: true,
    }

    renderAnalyticsPage()

    expect(
      screen.getByText('Analytics est disponible pour les propriétaires, directeurs et managers.'),
    ).toBeTruthy()
    expect(dashboardQueryMock).toHaveBeenCalledWith(
      expect.any(Object),
      expect.objectContaining({ enabled: false }),
    )
    expect(patternsQueryMock).toHaveBeenCalledWith(
      expect.any(Object),
      expect.objectContaining({ enabled: false }),
    )
  })

  it('enables the dashboard for Analytics memberships, including multi-membership users', () => {
    setDashboardQuery({ data: dashboard() })
    setPatternsQuery()
    setFilterOptionsQuery()
    authState.current = {
      bootstrap: bootstrap(['staff', 'manager']),
      isBootstrapping: false,
      isReady: true,
    }

    renderAnalyticsPage()

    expect(screen.getByText('Dashboard Analytics')).toBeTruthy()
    expect(dashboardQueryMock).toHaveBeenCalledWith(
      expect.objectContaining({
        periodStart: expect.any(String),
        periodEnd: expect.any(String),
        organizationId: null,
      }),
      expect.objectContaining({ enabled: true }),
    )
    expect(patternsQueryMock).toHaveBeenCalledWith(
      expect.objectContaining({
        establishmentIds: [],
        q: '',
        recurrence: 'all',
      }),
      expect.objectContaining({ enabled: true }),
    )
  })

  it('renders a loading state while the dashboard query is pending', () => {
    setDashboardQuery({ isLoading: true })
    setPatternsQuery()
    setFilterOptionsQuery()
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    renderAnalyticsPage()

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
    setPatternsQuery()
    setFilterOptionsQuery()
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    renderAnalyticsPage()

    expect(screen.getByText('Période invalide.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(refetchMock).toHaveBeenCalled()
  })

  it('renders dashboard KPI values from API comparison objects without recomputing deltas', () => {
    const navigateMock = vi.fn()
    setDashboardQuery({ data: dashboard() })
    setPatternsQuery({
      data: {
        pages: [
          {
            has_more: false,
            next_cursor: null,
            items: [
              {
                pattern_id: 'pattern-1',
                label: 'Retard livraison',
                normalized_label: 'retard-livraison',
                status: 'active',
                signal_count: 5,
                previous_signal_count: 3,
                signal_count_comparison: {
                  current_value: 5,
                  previous_value: 3,
                  absolute_delta: 2,
                  relative_change: 0.666,
                  relative_change_status: 'computed',
                },
                last_seen_at: '2026-08-12T08:30:00.000Z',
                actionable_signal_count: 2,
                establishment_count: 1,
                establishments: [
                  {
                    establishment_id: 'est-1',
                    name: 'Spore Marais',
                    signal_count: 5,
                  },
                ],
                is_recurrent: true,
                occurrence_count_30d: 4,
                distinct_day_count_30d: 2,
                recurrence_window: {
                  window_start: '2026-07-13T10:30:00.000Z',
                  window_end: '2026-08-12T10:30:00.000Z',
                },
                recurrence_status: 'computed',
              },
            ],
          },
        ],
      },
    })
    setFilterOptionsQuery()
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    renderAnalyticsPage({ onNavigate: navigateMock })

    expect(screen.getByText('Signals analysés')).toBeTruthy()
    expect(screen.getAllByText('8').length).toBeGreaterThan(0)
    expect(screen.getAllByText('+999').length).toBeGreaterThan(0)
    expect(screen.getByText('-2')).toBeTruthy()
    expect(screen.getAllByText(/12,5\s?%\s+vs précédent/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('non comparable').length).toBeGreaterThan(0)
    expect(screen.getByText('2 h')).toBeTruthy()
    expect(screen.getByText('Retard livraison')).toBeTruthy()
    expect(screen.getByText('Oui (4/2j)')).toBeTruthy()
    expect(screen.getAllByTestId('analytics-pattern-row')).toHaveLength(1)
    const patternLink = screen.getByRole('link', { name: /Retard livraison/ })
    expect(screen.getAllByRole('link', { name: /Retard livraison/ })).toHaveLength(1)
    expect(patternLink.className).toContain('lg:grid-cols-')
    expect(screen.getByTestId('analytics-pattern-list').parentElement?.className).toContain(
      'overflow-hidden',
    )
    expect(patternLink.getAttribute('href')).toContain('/analytics/patterns/pattern-1?')
    expect(patternLink.getAttribute('href')).toContain('period_start=')
    fireEvent.click(patternLink)
    expect(navigateMock).toHaveBeenCalledWith(
      expect.stringContaining('/analytics/patterns/pattern-1?'),
    )
  })

  it('renders backend classification coverage and technical breakdowns factually', () => {
    setDashboardQuery({ data: dashboard() })
    setPatternsQuery()
    setFilterOptionsQuery()
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    renderAnalyticsPage()

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

  it('renders period presets as a global Analytics control, outside Motifs filters', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-12T10:30:00.000Z'))
    setDashboardQuery({ data: dashboard() })
    setPatternsQuery()
    setFilterOptionsQuery()
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    renderAnalyticsPage()

    expect(screen.getByText('Période Analytics')).toBeTruthy()
    expect(
      screen.getByText('Contrôle global appliqué aux KPIs et à la liste des motifs.'),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: '7 jours' }).className).toContain('min-h-11')
    expect(screen.getByText('Filtres appliqués uniquement à la liste des motifs.')).toBeTruthy()
    expect(screen.queryByText('Période')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '7 jours' }))

    const params = new URLSearchParams(window.location.search)
    expect(params.get('period_start')).toBe('2026-08-05T10:30:00.000Z')
    expect(params.get('period_end')).toBe('2026-08-12T10:30:00.000Z')
    expect(dashboardQueryMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        periodStart: '2026-08-05T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
      }),
      expect.objectContaining({ enabled: true }),
    )
    expect(patternsQueryMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        periodStart: '2026-08-05T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
      }),
      expect.objectContaining({ enabled: true }),
    )
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
    setPatternsQuery()
    setFilterOptionsQuery()
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    renderAnalyticsPage()

    expect(screen.getByText('Aucune donnée Analytics visible')).toBeTruthy()
  })

  it('does not crash when Analytics query params are invalid', () => {
    window.history.replaceState(
      null,
      '',
      '/analytics?period_start=2026-13-01T00%3A00%3A00Z&establishment_id=ignored',
    )
    setDashboardQuery({ data: dashboard() })
    setPatternsQuery()
    setFilterOptionsQuery()
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    renderAnalyticsPage()

    expect(screen.getByText('Dashboard Analytics')).toBeTruthy()
    expect(dashboardQueryMock).toHaveBeenCalledWith(
      expect.objectContaining({ organizationId: null }),
      expect.objectContaining({ enabled: true }),
    )
  })

  it('debounces q writes with replace and does not overwrite newer URL state', () => {
    vi.useFakeTimers()
    window.history.replaceState(null, '', '/analytics')
    setDashboardQuery({ data: dashboard() })
    setPatternsQuery()
    setFilterOptionsQuery()
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    const history = renderAnalyticsPage()

    const input = screen.getByPlaceholderText('Nom du motif')
    fireEvent.change(input, { target: { value: 'retard' } })
    act(() => {
      history.navigate('/analytics?q=externe')
    })

    act(() => {
      vi.advanceTimersByTime(400)
    })

    expect(window.location.search).toBe('?q=externe')

    fireEvent.change(screen.getByPlaceholderText('Nom du motif'), {
      target: { value: 'final' },
    })
    act(() => {
      vi.advanceTimersByTime(400)
    })

    expect(window.location.search).toContain('q=final')
  })
})
