// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AnalyticsPatternDetailResponse } from '@/features/analytics/api'
import { AnalyticsApiError } from '@/features/analytics/api'
import { AnalyticsPatternDetailPage } from '@/features/analytics/pages/analytics-pattern-detail-page'
import type { AnalyticsUrlState } from '@/features/analytics/lib/analytics-url-state'

const detailQueryMock = vi.fn()

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
  useAnalyticsPatternDetailQuery: (...args: unknown[]) => detailQueryMock(...args),
}))

const analyticsState: AnalyticsUrlState = {
  periodStart: '2026-07-01T00:00:00.000Z',
  periodEnd: '2026-08-01T00:00:00.000Z',
  organizationId: '11111111-1111-4111-8111-111111111111',
  establishmentIds: ['22222222-2222-4222-8222-222222222222'],
  q: 'retard',
  recurrence: 'recurrent',
  responsibleBusinessUnitIds: ['33333333-3333-4333-8333-333333333333'],
  responsibleBusinessUnitUnassigned: true,
  signalStatuses: ['open'],
}

function bootstrap(role: string) {
  return {
    memberships: [
      {
        id: `member-${role}`,
        establishment_id: 'est-1',
        establishment_name: 'Spore 1',
        organization_id: 'org-1',
        organization_name: 'Spore',
        role,
        status: 'active',
        scopes: [],
        scope_summary: { business_unit_count: 0 },
      },
    ],
  }
}

function detail(overrides: Partial<AnalyticsPatternDetailResponse> = {}): AnalyticsPatternDetailResponse {
  return {
    identity: {
      pattern_id: '44444444-4444-4444-8444-444444444444',
      label: 'Retard livraison',
      status: 'active',
      created_at: '2026-07-13T10:30:00.000Z',
      merged_into_pattern_id: null,
    },
    current_period: {
      period_start: '2026-07-01T00:00:00.000Z',
      period_end: '2026-08-01T00:00:00.000Z',
    },
    previous_period: {
      period_start: '2026-06-01T00:00:00.000Z',
      period_end: '2026-07-01T00:00:00.000Z',
    },
    metrics: {
      signal_count: 8,
      previous_signal_count: 5,
      signal_count_comparison: {
        current_value: 8,
        previous_value: 5,
        absolute_delta: 3,
        relative_change: 0.6,
        relative_change_status: 'computed',
      },
      actionable_signal_count: 2,
      last_seen_at: '2026-07-31T08:30:00.000Z',
      establishment_count: 2,
    },
    is_recurrent: true,
    occurrence_count_30d: 4,
    distinct_day_count_30d: 2,
    recurrence_window: {
      window_start: '2026-07-02T00:00:00.000Z',
      window_end: '2026-08-01T00:00:00.000Z',
    },
    recurrence_status: 'computed',
    trend_timezone: 'UTC',
    trend: [
      {
        bucket_date: '2026-07-31',
        bucket_start: '2026-07-31T00:00:00.000Z',
        bucket_end: '2026-08-01T00:00:00.000Z',
        signal_count: 8,
      },
    ],
    status_distribution: [{ status: 'open', signal_count: 8 }],
    establishments: [
      {
        establishment_id: 'est-1',
        name: 'Spore Marais',
        signal_count: 5,
      },
    ],
    establishment_bucket_count: 2,
    establishment_other_signal_count: 3,
    responsible_business_units: [
      {
        business_unit_id: null,
        name: 'Non assigné',
        signal_count: 2,
      },
    ],
    business_unit_bucket_count: 1,
    business_unit_other_signal_count: 0,
    drilldown_context: {
      pattern_id: '44444444-4444-4444-8444-444444444444',
      period_start: '2026-07-01T00:00:00.000Z',
      period_end: '2026-08-01T00:00:00.000Z',
      organization_id: '11111111-1111-4111-8111-111111111111',
      establishment_id: null,
    },
    ...overrides,
  }
}

function setDetailQuery(value: ReturnType<typeof detailQueryMock> = {}) {
  detailQueryMock.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...value,
  })
}

describe('AnalyticsPatternDetailPage', () => {
  afterEach(() => {
    cleanup()
    detailQueryMock.mockReset()
    authState.current = {
      bootstrap: null,
      isBootstrapping: false,
      isReady: true,
    }
  })

  it('does not fetch for Staff-only users', () => {
    setDetailQuery()
    authState.current = {
      bootstrap: bootstrap('staff'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(
      screen.getByText('Analytics est disponible pour les propriétaires, directeurs et managers.'),
    ).toBeTruthy()
    expect(detailQueryMock).toHaveBeenCalledWith(
      'pattern-1',
      analyticsState,
      expect.objectContaining({ enabled: false }),
    )
  })

  it('renders backend detail fields without using a second URL state hook', () => {
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(detailQueryMock).toHaveBeenCalledWith(
      'pattern-1',
      analyticsState,
      expect.objectContaining({ enabled: true }),
    )
    expect(screen.getByRole('heading', { name: 'Retard livraison' })).toBeTruthy()
    expect(screen.getByText('Récurrent')).toBeTruthy()
    expect(screen.getByText('Tendance journalière')).toBeTruthy()
    expect(screen.getByText('Distribution par statut')).toBeTruthy()
    expect(screen.getByText('Établissements concernés')).toBeTruthy()
    expect(screen.getByText('BU responsables')).toBeTruthy()
    expect(screen.queryByText(/raw/i)).toBeNull()
    expect(screen.queryByText(/prompt/i)).toBeNull()
  })

  it('uses the backend bucket civil date for trend labels', () => {
    setDetailQuery({
      data: detail({
        trend_timezone: 'Pacific/Honolulu',
        trend: [
          {
            bucket_date: '2026-07-31',
            bucket_start: '2026-08-01T00:30:00.000Z',
            bucket_end: '2026-08-01T23:30:00.000Z',
            signal_count: 3,
          },
        ],
      }),
    })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(screen.getByText('31 juil.')).toBeTruthy()
    expect(screen.queryByText('01 août')).toBeNull()
  })

  it('uses the provided analytics state for Back navigation', () => {
    const navigate = vi.fn()
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={navigate}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Retour aux motifs' }))

    expect(navigate).toHaveBeenCalledWith(
      '/analytics?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&organization_id=11111111-1111-4111-8111-111111111111&establishment_ids=22222222-2222-4222-8222-222222222222&q=retard&recurrence=recurrent&responsible_business_unit_ids=33333333-3333-4333-8333-333333333333&responsible_business_unit_unassigned=true&signal_statuses=open',
    )
  })

  it('renders not found as a non-revealing state', () => {
    setDetailQuery({
      isError: true,
      error: new AnalyticsApiError({
        status: 404,
        detail: 'Introuvable.',
        code: 'analytics_pattern_not_found',
      }),
    })
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(screen.getByText('Motif introuvable')).toBeTruthy()
    expect(screen.getByText(/introuvable ou non accessible/)).toBeTruthy()
  })
})
