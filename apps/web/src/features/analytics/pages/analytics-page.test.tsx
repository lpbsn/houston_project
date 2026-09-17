// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { createMemoryHistory, type AppHistory } from '@/app/app-history'
import { AppRouteProvider } from '@/app/app-routes'
import type { AnalyticsDashboardResponse } from '@/features/analytics/api'
import { AnalyticsApiError } from '@/features/analytics/api'
import { dashboardCoverageBannerMessage } from '@/features/analytics/lib/dashboard-comparisons'
import {
  dashboardComparison,
  dashboardResponseFixture,
} from '@/features/analytics/lib/dashboard-test-fixture'
import { AnalyticsPage } from '@/features/analytics/pages/analytics-page'

const dashboardQueryMock = vi.fn()
const rankingsQueryMock = vi.fn()

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
  useAnalyticsDashboardRankingsInfiniteQuery: (...args: unknown[]) => rankingsQueryMock(...args),
}))

function dashboard(
  overrides: Partial<AnalyticsDashboardResponse> = {},
): AnalyticsDashboardResponse {
  return dashboardResponseFixture(overrides)
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
      establishment_name: 'Nord',
      role: 'manager',
      status: 'active',
    },
  }
}

function renderAnalyticsPage(href = '/e/est-1'): AppHistory {
  const history = createMemoryHistory(href)
  render(
    createElement(
      AppRouteProvider,
      { history },
      createElement(AnalyticsPage, {
        scope: { type: 'establishment', establishmentId: 'est-1' },
      }),
    ),
  )
  return history
}

afterEach(() => {
  cleanup()
  dashboardQueryMock.mockReset()
  rankingsQueryMock.mockReset()
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

    const history = renderAnalyticsPage('/e/est-1?period=7d')
    fireEvent.click(screen.getByRole('button', { name: '15 j' }))
    expect(history.getHref()).toBe('/e/est-1?period=15d')
  })

  it('hides percent deltas when coverage is not complete', () => {
    authState.current.bootstrap = managerBootstrap()
    dashboardQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: dashboard({
        plan_deadline_respect: {
          ...dashboard().plan_deadline_respect,
          early_comparison: dashboardComparison(0.21, 'partial'),
        },
      }),
      refetch: vi.fn(),
    })
    rankingsQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        pages: [
          {
            items: [
              {
                pattern_id: '22222222-2222-4222-8222-222222222227',
                name: 'Motif 6 caché',
                first_seen_at: '2026-08-16T12:00:00.000Z',
              },
            ],
          },
        ],
      },
      hasNextPage: false,
    })

    renderAnalyticsPage()
    const banner = dashboardCoverageBannerMessage({
      coverage: 'partial',
      historyReliableFrom: '2026-01-01T00:00:00.000Z',
      hasDisplayableDelta: true,
    })
    expect(banner).toBeTruthy()
    expect(screen.getByText(banner as string)).toBeTruthy()
    expect(screen.queryByText('Données incomplètes')).toBeNull()
    expect(screen.queryByText('Motif 6 caché')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Voir tout' }))
    expect(screen.getByText('Motif 6 caché')).toBeTruthy()
  })

  it('omits the coverage banner when every comparison is complete', () => {
    authState.current.bootstrap = managerBootstrap()
    dashboardQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: dashboard(),
      refetch: vi.fn(),
    })

    renderAnalyticsPage()
    expect(
      screen.queryByText(
        dashboardCoverageBannerMessage({
          coverage: 'partial',
          historyReliableFrom: '2026-01-01T00:00:00.000Z',
          hasDisplayableDelta: true,
        }) as string,
      ),
    ).toBeNull()
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

  it('renders the ten operational cards without drag-and-drop copy', () => {
    authState.current.bootstrap = managerBootstrap()
    dashboardQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: dashboard(),
      refetch: vi.fn(),
    })

    renderAnalyticsPage()
    const headings = screen.getAllByRole('heading').map((node) => node.textContent)
    expect(headings).toEqual(
      expect.arrayContaining([
        'Dashboard',
        'Sujets récurrents',
        'Nouveaux sujets',
        'Nombre d’observations',
        'Destination des observations',
        'Délai avant chaque destination',
        'Délais et taux de résolution des plans d’action',
        'Plan d’action en retard',
        'Qualité des résolutions de plans d’action',
        'Classement des contributeurs',
        'Lieux les plus cités',
      ]),
    )
    expect(screen.queryByText(/glissez-déposez/i)).toBeNull()
    expect(screen.getAllByText('Bientôt disponible').length).toBeGreaterThan(0)
  })

  it('exposes period controls and dashboard widgets without fake confidence copy', () => {
    authState.current.bootstrap = managerBootstrap()
    dashboardQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: dashboard(),
      refetch: vi.fn(),
    })

    renderAnalyticsPage()
    for (const days of ['3 j', '7 j', '15 j', '30 j', '90 j']) {
      expect(screen.getByRole('button', { name: days })).toBeTruthy()
    }
    expect(screen.getByRole('button', { name: /Exporter/ })).toBeTruthy()
    expect(screen.getAllByText('Bientôt disponible').length).toBeGreaterThan(0)
    expect(screen.getByText('7 derniers jours · jusqu’à maintenant · comparé aux 7 jours précédents')).toBeTruthy()
    expect(screen.getByText('Cuisine')).toBeTruthy()
    expect(screen.getByText('Terminé en avance')).toBeTruthy()
    expect(screen.getByText('Terminé à temps')).toBeTruthy()
    expect(screen.getByText('Terminé en retard')).toBeTruthy()
    expect(screen.queryByText(/confiance/i)).toBeNull()
    expect(screen.queryByText(/taux de confiance/i)).toBeNull()
  })
})
