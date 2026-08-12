import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()

vi.mock('@/api/client', () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
  },
  withAuthRetry: async (callback: (token: string) => Promise<unknown>) =>
    callback('test-token'),
}))

import {
  AnalyticsApiError,
  analyticsQueryKeys,
  fetchAnalyticsDashboard,
  fetchAnalyticsPatternDetail,
  fetchAnalyticsPatternFilterOptions,
  fetchAnalyticsPatterns,
  type AnalyticsDashboardResponse,
} from './api'

const dashboardResponse = {
  current_period: {
    period_start: '2026-07-13T10:30:00.000Z',
    period_end: '2026-08-12T10:30:00.000Z',
  },
  previous_period: {
    period_start: '2026-06-13T10:30:00.000Z',
    period_end: '2026-07-13T10:30:00.000Z',
  },
  current_kpis: {
    analytics_signal_population_count: 0,
    signals_analyzed_count: 0,
    operational_patterns_count: 0,
    actionable_signals_count: 0,
    median_resolution_seconds: null,
    resolution_time_signal_count: 0,
    invalid_resolution_duration_count: 0,
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
    recurring_patterns_count: 0,
    recurrence_window: {
      window_start: '2026-07-13T10:30:00.000Z',
      window_end: '2026-08-12T10:30:00.000Z',
    },
    recurrence_status: 'computed',
  },
  previous_kpis: {
    analytics_signal_population_count: 0,
    signals_analyzed_count: 0,
    operational_patterns_count: 0,
    actionable_signals_count: 0,
    median_resolution_seconds: null,
    resolution_time_signal_count: 0,
    invalid_resolution_duration_count: 0,
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
    recurring_patterns_count: 0,
    recurrence_window: {
      window_start: '2026-06-13T10:30:00.000Z',
      window_end: '2026-07-13T10:30:00.000Z',
    },
    recurrence_status: 'computed',
  },
  signals_analyzed_count: {
    current_value: 0,
    previous_value: 0,
    absolute_delta: 0,
    relative_change: null,
    relative_change_status: 'undefined_previous_zero',
  },
  operational_patterns_count: {
    current_value: 0,
    previous_value: 0,
    absolute_delta: 0,
    relative_change: null,
    relative_change_status: 'undefined_previous_zero',
  },
  actionable_signals_count: {
    current_value: 0,
    previous_value: 0,
    absolute_delta: 0,
    relative_change: null,
    relative_change_status: 'undefined_previous_zero',
  },
  median_resolution_seconds: {
    current_value: null,
    previous_value: null,
    absolute_delta: null,
    relative_change: null,
    relative_change_status: 'not_applicable',
  },
  recurring_patterns_count: {
    current_value: 0,
    previous_value: 0,
    absolute_delta: 0,
    relative_change: null,
    relative_change_status: 'undefined_previous_zero',
  },
  recurrence_status: 'computed',
} satisfies AnalyticsDashboardResponse

describe('analytics api', () => {
  beforeEach(() => {
    getMock.mockReset()
    getMock.mockResolvedValue({
      data: dashboardResponse,
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })
  })

  it('fetches the dashboard with the resolved analytics URL state only', async () => {
    await fetchAnalyticsDashboard({
      periodStart: '2026-07-13T10:30:00.000Z',
      periodEnd: '2026-08-12T10:30:00.000Z',
      organizationId: '11111111-1111-4111-8111-111111111111',
    })

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/analytics/dashboard/',
      expect.objectContaining({
        params: {
          query: {
            period_start: '2026-07-13T10:30:00.000Z',
            period_end: '2026-08-12T10:30:00.000Z',
            organization_id: '11111111-1111-4111-8111-111111111111',
          },
        },
        headers: { Authorization: 'Bearer test-token' },
      }),
    )
    expect(getMock.mock.calls[0]?.[1]?.params?.query).not.toHaveProperty('establishment_id')
  })

  it('omits organization_id when it is absent', async () => {
    await fetchAnalyticsDashboard({
      periodStart: '2026-07-13T10:30:00.000Z',
      periodEnd: '2026-08-12T10:30:00.000Z',
      organizationId: null,
    })

    expect(getMock.mock.calls[0]?.[1]?.params?.query).toEqual({
      period_start: '2026-07-13T10:30:00.000Z',
      period_end: '2026-08-12T10:30:00.000Z',
    })
  })

  it('maps dashboard API errors', async () => {
    getMock.mockResolvedValue({
      data: undefined,
      error: { detail: 'Période invalide.', code: 'analytics_period_invalid' },
      response: { ok: false, status: 400 } as Response,
    })

    await expect(
      fetchAnalyticsDashboard({
        periodStart: '2026-07-13T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
        organizationId: null,
      }),
    ).rejects.toMatchObject({
      code: 'analytics_period_invalid',
      detail: 'Période invalide.',
      status: 400,
    })

    await expect(
      fetchAnalyticsDashboard({
        periodStart: '2026-07-13T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
        organizationId: null,
      }),
    ).rejects.toBeInstanceOf(AnalyticsApiError)
  })

  it('keeps dashboard query keys stable from URL state', () => {
    expect(
      analyticsQueryKeys.dashboard({
        periodStart: '2026-07-13T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
        organizationId: null,
      }),
    ).toEqual([
      'analytics',
      'dashboard',
      {
        periodStart: '2026-07-13T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
        organizationId: null,
      },
    ])
  })

  it('fetches patterns with table filters and no singular establishment_id', async () => {
    getMock.mockResolvedValue({
      data: {
        current_period: {
          period_start: '2026-07-13T10:30:00.000Z',
          period_end: '2026-08-12T10:30:00.000Z',
        },
        previous_period: {
          period_start: '2026-06-13T10:30:00.000Z',
          period_end: '2026-07-13T10:30:00.000Z',
        },
        items: [],
        total_count: 0,
        page_size: 50,
        has_more: false,
        next_cursor: null,
        recurrence_window: {
          window_start: '2026-07-13T10:30:00.000Z',
          window_end: '2026-08-12T10:30:00.000Z',
        },
        recurrence_status: 'computed',
      },
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })

    await fetchAnalyticsPatterns(
      {
        periodStart: '2026-07-13T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
        organizationId: '11111111-1111-4111-8111-111111111111',
        establishmentIds: ['22222222-2222-4222-8222-222222222222'],
        q: 'retard',
        recurrence: 'recurrent',
        responsibleBusinessUnitIds: ['33333333-3333-4333-8333-333333333333'],
        responsibleBusinessUnitUnassigned: true,
        signalStatuses: ['open', 'archived'],
      },
      { cursor: 'cursor-1', pageSize: 25 },
    )

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/analytics/patterns/',
      expect.objectContaining({
        params: {
          query: {
            period_start: '2026-07-13T10:30:00.000Z',
            period_end: '2026-08-12T10:30:00.000Z',
            organization_id: '11111111-1111-4111-8111-111111111111',
            establishment_ids: '22222222-2222-4222-8222-222222222222',
            q: 'retard',
            recurrence: 'recurrent',
            responsible_business_unit_ids: '33333333-3333-4333-8333-333333333333',
            responsible_business_unit_unassigned: true,
            signal_statuses: 'open,archived',
            cursor: 'cursor-1',
            page_size: 25,
          },
        },
      }),
    )
    expect(getMock.mock.calls[0]?.[1]?.params?.query).not.toHaveProperty('establishment_id')
  })

  it('fetches pattern filter options through the generated endpoint contract', async () => {
    getMock.mockResolvedValue({
      data: {
        establishments: [],
        responsible_business_units: [],
        includes_unassigned: false,
      },
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })

    await fetchAnalyticsPatternFilterOptions({
      periodStart: '2026-07-13T10:30:00.000Z',
      periodEnd: '2026-08-12T10:30:00.000Z',
      organizationId: '11111111-1111-4111-8111-111111111111',
      establishmentIds: [
        '22222222-2222-4222-8222-222222222222',
        '44444444-4444-4444-8444-444444444444',
      ],
      q: 'ignored for options',
      recurrence: 'recurrent',
      responsibleBusinessUnitIds: ['33333333-3333-4333-8333-333333333333'],
      responsibleBusinessUnitUnassigned: true,
      signalStatuses: ['open'],
    })

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/analytics/pattern-filter-options/',
      expect.objectContaining({
        params: {
          query: {
            organization_id: '11111111-1111-4111-8111-111111111111',
            establishment_ids:
              '22222222-2222-4222-8222-222222222222,44444444-4444-4444-8444-444444444444',
          },
        },
        headers: { Authorization: 'Bearer test-token' },
      }),
    )
    expect(getMock.mock.calls[0]?.[1]?.params?.query).not.toHaveProperty('establishment_id')
    expect(getMock.mock.calls[0]?.[1]?.params?.query).not.toHaveProperty('q')
    expect(getMock.mock.calls[0]?.[1]?.params?.query).not.toHaveProperty('recurrence')
  })

  it('fetches pattern detail with only endpoint-supported query params', async () => {
    getMock.mockResolvedValue({
      data: {
        identity: {
          pattern_id: '44444444-4444-4444-8444-444444444444',
          label: 'Retard livraison',
          normalized_label: 'retard livraison',
          status: 'active',
          created_at: '2026-07-13T10:30:00.000Z',
          merged_into_pattern_id: null,
        },
        current_period: {
          period_start: '2026-07-13T10:30:00.000Z',
          period_end: '2026-08-12T10:30:00.000Z',
        },
        previous_period: {
          period_start: '2026-06-13T10:30:00.000Z',
          period_end: '2026-07-13T10:30:00.000Z',
        },
        metrics: {
          signal_count: 1,
          previous_signal_count: 0,
          signal_count_comparison: {
            current_value: 1,
            previous_value: 0,
            absolute_delta: 1,
            relative_change: null,
            relative_change_status: 'undefined_previous_zero',
          },
          actionable_signal_count: 1,
          last_seen_at: '2026-08-12T08:30:00.000Z',
          establishment_count: 1,
        },
        is_recurrent: false,
        occurrence_count_30d: 0,
        distinct_day_count_30d: 0,
        recurrence_window: {
          window_start: '2026-07-13T10:30:00.000Z',
          window_end: '2026-08-12T10:30:00.000Z',
        },
        recurrence_status: 'computed',
        trend_timezone: 'UTC',
        trend: [],
        status_distribution: [],
        establishments: [],
        establishment_bucket_count: 0,
        establishment_other_signal_count: 0,
        responsible_business_units: [],
        business_unit_bucket_count: 0,
        business_unit_other_signal_count: 0,
        drilldown_context: {
          pattern_id: '44444444-4444-4444-8444-444444444444',
          period_start: '2026-07-13T10:30:00.000Z',
          period_end: '2026-08-12T10:30:00.000Z',
          organization_id: '11111111-1111-4111-8111-111111111111',
          establishment_id: null,
        },
      },
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })

    await fetchAnalyticsPatternDetail('44444444-4444-4444-8444-444444444444', {
      periodStart: '2026-07-13T10:30:00.000Z',
      periodEnd: '2026-08-12T10:30:00.000Z',
      organizationId: '11111111-1111-4111-8111-111111111111',
      establishmentIds: ['22222222-2222-4222-8222-222222222222'],
      q: 'retard',
      recurrence: 'recurrent',
      responsibleBusinessUnitIds: ['33333333-3333-4333-8333-333333333333'],
      responsibleBusinessUnitUnassigned: true,
      signalStatuses: ['open'],
    })

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/analytics/patterns/{pattern_id}/',
      expect.objectContaining({
        params: {
          path: { pattern_id: '44444444-4444-4444-8444-444444444444' },
          query: {
            period_start: '2026-07-13T10:30:00.000Z',
            period_end: '2026-08-12T10:30:00.000Z',
            organization_id: '11111111-1111-4111-8111-111111111111',
          },
        },
        headers: { Authorization: 'Bearer test-token' },
      }),
    )
    expect(getMock.mock.calls[0]?.[1]?.params?.query).not.toHaveProperty('establishment_id')
    expect(getMock.mock.calls[0]?.[1]?.params?.query).not.toHaveProperty('establishment_ids')
    expect(getMock.mock.calls[0]?.[1]?.params?.query).not.toHaveProperty('q')
    expect(getMock.mock.calls[0]?.[1]?.params?.query).not.toHaveProperty('recurrence')
  })
})
