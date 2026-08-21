import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const postMock = vi.fn()

vi.mock('@/api/client', () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
    POST: (...args: unknown[]) => postMock(...args),
  },
  withAuthRetry: async (callback: (token: string) => Promise<unknown>) =>
    callback('test-token'),
}))

import {
  AnalyticsApiError,
  analyticsQueryKeys,
  fetchAnalyticsDashboard,
  fetchAnalyticsPatternGovernanceTargets,
  fetchAnalyticsPatternDetail,
  fetchAnalyticsPatternFilterOptions,
  fetchAnalyticsPatternSignals,
  fetchAnalyticsPatterns,
  mergeAnalyticsPatterns,
  moveAnalyticsPatternSignals,
  renameAnalyticsPattern,
  reportAnalyticsPatternIssue,
  splitAnalyticsPatternToExisting,
  splitAnalyticsPatternToNew,
  type AnalyticsDashboardResponse,
} from './api'

const dashboardResponse = {
  period_days: 7,
  current_period: {
    period_start: '2026-07-13T10:30:00.000Z',
    period_end: '2026-08-12T10:30:00.000Z',
  },
  previous_period: {
    period_start: '2026-06-13T10:30:00.000Z',
    period_end: '2026-07-13T10:30:00.000Z',
  },
  history_reliable_from: '2026-01-01T00:00:00.000Z',
  scope_type: 'cross',
  establishment_id: null,
  establishment_ids: [],
  recurring_patterns: [],
  new_patterns: [],
  new_patterns_preview_limit: 5,
  contributors: [],
  observation_delay_canceled: {
    median_seconds: null,
    mean_seconds: null,
    p90_seconds: null,
    n: 0,
    comparison: {
      current_value: null,
      previous_value: null,
      absolute_delta: null,
      relative_change: null,
      relative_change_status: 'not_applicable',
      coverage: 'complete',
    },
  },
  observation_delay_resolved: {
    median_seconds: null,
    mean_seconds: null,
    p90_seconds: null,
    n: 0,
    comparison: {
      current_value: null,
      previous_value: null,
      absolute_delta: null,
      relative_change: null,
      relative_change_status: 'not_applicable',
      coverage: 'complete',
    },
  },
  observation_delay_transformed: {
    median_seconds: null,
    mean_seconds: null,
    p90_seconds: null,
    n: 0,
    comparison: {
      current_value: null,
      previous_value: null,
      absolute_delta: null,
      relative_change: null,
      relative_change_status: 'not_applicable',
      coverage: 'complete',
    },
  },
  operational_resolution_rate: {
    current_value: null,
    previous_value: null,
    absolute_delta: null,
    relative_change: null,
    relative_change_status: 'not_applicable',
    coverage: 'complete',
  },
  closure_resolved_share: {
    current_value: null,
    previous_value: null,
    absolute_delta: null,
    relative_change: null,
    relative_change_status: 'not_applicable',
    coverage: 'complete',
  },
  reopenings: {
    current_value: 0,
    previous_value: 0,
    absolute_delta: 0,
    relative_change: null,
    relative_change_status: 'undefined_previous_zero',
    coverage: 'complete',
  },
  open_observation_count: 0,
  aging_buckets: [],
  aging_over_15d_share: {
    current_value: null,
    previous_value: null,
    absolute_delta: null,
    relative_change: null,
    relative_change_status: 'not_applicable',
    coverage: 'complete',
  },
  plan_delay_canceled: {
    median_seconds: null,
    mean_seconds: null,
    p90_seconds: null,
    n: 0,
    comparison: {
      current_value: null,
      previous_value: null,
      absolute_delta: null,
      relative_change: null,
      relative_change_status: 'not_applicable',
      coverage: 'complete',
    },
  },
  plan_delay_resolved: {
    median_seconds: null,
    mean_seconds: null,
    p90_seconds: null,
    n: 0,
    comparison: {
      current_value: null,
      previous_value: null,
      absolute_delta: null,
      relative_change: null,
      relative_change_status: 'not_applicable',
      coverage: 'complete',
    },
  },
  plan_validation: {
    median_seconds: null,
    mean_seconds: null,
    p90_seconds: null,
    n: 0,
    comparison: {
      current_value: null,
      previous_value: null,
      absolute_delta: null,
      relative_change: null,
      relative_change_status: 'not_applicable',
      coverage: 'complete',
    },
  },
  plan_deadlines: {
    early: null,
    on_time: null,
    late: null,
    n: 0,
    early_comparison: {
      current_value: null,
      previous_value: null,
      absolute_delta: null,
      relative_change: null,
      relative_change_status: 'not_applicable',
      coverage: 'complete',
    },
    on_time_comparison: {
      current_value: null,
      previous_value: null,
      absolute_delta: null,
      relative_change: null,
      relative_change_status: 'not_applicable',
      coverage: 'complete',
    },
    late_comparison: {
      current_value: null,
      previous_value: null,
      absolute_delta: null,
      relative_change: null,
      relative_change_status: 'not_applicable',
      coverage: 'complete',
    },
  },
  zones: [],
  zones_preview_limit: 7,
  poles: [],
} satisfies AnalyticsDashboardResponse

describe('analytics api', () => {
  beforeEach(() => {
    getMock.mockReset()
    postMock.mockReset()
    getMock.mockResolvedValue({
      data: dashboardResponse,
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })
  })

  it('fetches the dashboard with period_days and no establishment in Cross', async () => {
    await fetchAnalyticsDashboard({
      periodDays: 7,
      establishmentId: null,
    })

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/analytics/dashboard/',
      expect.objectContaining({
        params: {
          query: {
            period_days: 7,
          },
        },
        headers: { Authorization: 'Bearer test-token' },
      }),
    )
    expect(getMock.mock.calls[0]?.[1]?.params?.query).not.toHaveProperty('establishment_id')
  })

  it('includes establishment_id when an establishment dashboard is requested', async () => {
    await fetchAnalyticsDashboard({
      periodDays: 15,
      establishmentId: '22222222-2222-4222-8222-222222222222',
    })

    expect(getMock.mock.calls[0]?.[1]?.params?.query).toEqual({
      period_days: 15,
      establishment_id: '22222222-2222-4222-8222-222222222222',
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
        periodDays: 7,
        establishmentId: null,
      }),
    ).rejects.toMatchObject({
      code: 'analytics_period_invalid',
      detail: 'Période invalide.',
      status: 400,
    })

    await expect(
      fetchAnalyticsDashboard({
        periodDays: 7,
        establishmentId: null,
      }),
    ).rejects.toBeInstanceOf(AnalyticsApiError)
  })

  it('keeps dashboard query keys stable from period and establishment', () => {
    expect(
      analyticsQueryKeys.dashboard({
        periodDays: 7,
        establishmentId: null,
      }),
    ).toEqual([
      'analytics',
      'dashboard',
      {
        periodDays: 7,
        establishmentId: null,
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

  it('fetches pattern signals with only endpoint-supported query params', async () => {
    getMock.mockResolvedValue({
      data: {
        period: {
          period_start: '2026-07-13T10:30:00.000Z',
          period_end: '2026-08-12T10:30:00.000Z',
        },
        items: [],
        page_size: 25,
        has_more: false,
        next_cursor: null,
      },
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })

    await fetchAnalyticsPatternSignals(
      '44444444-4444-4444-8444-444444444444',
      {
        periodStart: '2026-07-13T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
        organizationId: '11111111-1111-4111-8111-111111111111',
        establishmentIds: ['22222222-2222-4222-8222-222222222222'],
        q: 'retard',
        recurrence: 'recurrent',
        responsibleBusinessUnitIds: ['33333333-3333-4333-8333-333333333333'],
        responsibleBusinessUnitUnassigned: true,
        signalStatuses: ['open'],
      },
      { cursor: 'cursor-1', pageSize: 25 },
    )

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/analytics/patterns/{pattern_id}/signals/',
      expect.objectContaining({
        params: {
          path: { pattern_id: '44444444-4444-4444-8444-444444444444' },
          query: {
            period_start: '2026-07-13T10:30:00.000Z',
            period_end: '2026-08-12T10:30:00.000Z',
            organization_id: '11111111-1111-4111-8111-111111111111',
            cursor: 'cursor-1',
            page_size: 25,
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

  it('posts a pattern issue report through the generated endpoint contract', async () => {
    postMock.mockResolvedValue({
      data: {
        report_id: '66666666-6666-4666-8666-666666666666',
        pattern_id: '44444444-4444-4444-8444-444444444444',
        signal_id: '55555555-5555-4555-8555-555555555555',
        status: 'open',
        report_type: 'wrong_pattern',
        comment: 'Mauvais motif',
        created_at: '2026-08-13T10:00:00.000Z',
      },
      error: undefined,
      response: { ok: true, status: 201 } as Response,
    })

    await reportAnalyticsPatternIssue(
      '44444444-4444-4444-8444-444444444444',
      '55555555-5555-4555-8555-555555555555',
      {
        reason: 'wrong_pattern',
        comment: 'Mauvais motif',
      },
    )

    expect(postMock).toHaveBeenCalledWith(
      '/api/v1/analytics/patterns/{pattern_id}/signals/{signal_id}/issue-report/',
      expect.objectContaining({
        params: {
          path: {
            pattern_id: '44444444-4444-4444-8444-444444444444',
            signal_id: '55555555-5555-4555-8555-555555555555',
          },
        },
        body: {
          reason: 'wrong_pattern',
          comment: 'Mauvais motif',
        },
        headers: { Authorization: 'Bearer test-token' },
      }),
    )
  })

  it('fetches owner governance targets through the generated paginated endpoint', async () => {
    getMock.mockResolvedValue({
      data: {
        items: [],
        page_size: 20,
        has_more: false,
        next_cursor: null,
      },
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })

    await fetchAnalyticsPatternGovernanceTargets(
      '44444444-4444-4444-8444-444444444444',
      {
        q: 'retard',
        cursor: 'cursor-1',
        pageSize: 20,
      },
    )

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/analytics/patterns/{pattern_id}/governance-targets/',
      expect.objectContaining({
        params: {
          path: { pattern_id: '44444444-4444-4444-8444-444444444444' },
          query: {
            q: 'retard',
            cursor: 'cursor-1',
            page_size: 20,
          },
        },
        headers: { Authorization: 'Bearer test-token' },
      }),
    )
  })

  it('posts owner governance mutations through generated endpoint contracts', async () => {
    postMock.mockResolvedValue({
      data: {
        source_pattern: {
          pattern_id: '44444444-4444-4444-8444-444444444444',
          label: 'Source',
          normalized_label: 'source',
          status: 'active',
          merged_into_pattern_id: null,
        },
        target_pattern: null,
        moved_signal_count: 0,
        target_created: false,
      },
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })

    await renameAnalyticsPattern('44444444-4444-4444-8444-444444444444', {
      label: 'Nouveau',
    })
    await mergeAnalyticsPatterns('44444444-4444-4444-8444-444444444444', {
      target_pattern_id: '77777777-7777-4777-8777-777777777777',
    })
    await moveAnalyticsPatternSignals('44444444-4444-4444-8444-444444444444', {
      target_pattern_id: '77777777-7777-4777-8777-777777777777',
      signal_ids: ['55555555-5555-4555-8555-555555555555'],
    })
    await splitAnalyticsPatternToExisting('44444444-4444-4444-8444-444444444444', {
      target_pattern_id: '77777777-7777-4777-8777-777777777777',
      signal_ids: ['55555555-5555-4555-8555-555555555555'],
    })
    await splitAnalyticsPatternToNew('44444444-4444-4444-8444-444444444444', {
      label: 'Nouveau split',
      signal_ids: ['55555555-5555-4555-8555-555555555555'],
    })

    expect(postMock).toHaveBeenNthCalledWith(
      1,
      '/api/v1/analytics/patterns/{pattern_id}/rename/',
      expect.objectContaining({
        params: { path: { pattern_id: '44444444-4444-4444-8444-444444444444' } },
        body: { label: 'Nouveau' },
      }),
    )
    expect(postMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/analytics/patterns/{pattern_id}/merge/',
      expect.objectContaining({
        body: { target_pattern_id: '77777777-7777-4777-8777-777777777777' },
      }),
    )
    expect(postMock).toHaveBeenNthCalledWith(
      3,
      '/api/v1/analytics/patterns/{pattern_id}/move-signals/',
      expect.objectContaining({
        body: {
          target_pattern_id: '77777777-7777-4777-8777-777777777777',
          signal_ids: ['55555555-5555-4555-8555-555555555555'],
        },
      }),
    )
    expect(postMock).toHaveBeenNthCalledWith(
      4,
      '/api/v1/analytics/patterns/{pattern_id}/split-to-existing/',
      expect.objectContaining({
        body: {
          target_pattern_id: '77777777-7777-4777-8777-777777777777',
          signal_ids: ['55555555-5555-4555-8555-555555555555'],
        },
      }),
    )
    expect(postMock).toHaveBeenNthCalledWith(
      5,
      '/api/v1/analytics/patterns/{pattern_id}/split-to-new/',
      expect.objectContaining({
        body: {
          label: 'Nouveau split',
          signal_ids: ['55555555-5555-4555-8555-555555555555'],
        },
      }),
    )
  })
})
