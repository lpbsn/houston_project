import type {
  AnalyticsDashboardMetricComparison,
  AnalyticsDashboardResponse,
} from '@/features/analytics/api'

export function dashboardComparison(
  currentValue: number | null,
  coverage: AnalyticsDashboardMetricComparison['coverage'] = 'complete',
  relativeChange: number | null = 0.1,
): AnalyticsDashboardMetricComparison {
  return {
    current_value: currentValue,
    previous_value: 1,
    absolute_delta: 1,
    relative_change: relativeChange,
    relative_change_status: coverage === 'complete' ? 'computed' : 'not_applicable',
    coverage,
  }
}

function destination(share: number, coverage: AnalyticsDashboardMetricComparison['coverage'] = 'complete') {
  return {
    count: Math.round(share * 10),
    share,
    comparison: dashboardComparison(share, coverage),
  }
}

function delay(meanSeconds: number | null = 86400) {
  return {
    mean_seconds: meanSeconds,
    n: meanSeconds == null ? 0 : 2,
    undatable_in_scope: 0,
  }
}

function volumeWindow(offset: number, labelKey: string, total: number) {
  return {
    offset,
    label_key: labelKey,
    total,
    segments: [
      {
        pole_id: 'salle',
        name: 'Salle',
        count: total,
        share: 1,
      },
    ],
  }
}

function volume(coverage: AnalyticsDashboardMetricComparison['coverage'] = 'complete') {
  return {
    windows: [
      volumeWindow(-4, 'four_periods_ago', 52),
      volumeWindow(-3, 'three_periods_ago', 61),
      volumeWindow(-2, 'two_periods_ago', 58),
      volumeWindow(-1, 'previous', 72),
      volumeWindow(0, 'current', 78),
    ],
    current_total: 78,
    comparison: dashboardComparison(78, coverage, 0.09),
  }
}

export function dashboardResponseFixture(
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
    establishment_id: 'est-1',
    establishment_name: 'Nord',
    recurring_patterns: {
      items: [
        {
          pattern_id: '11111111-1111-4111-8111-111111111111',
          name: 'Chaîne du froid',
          signal_count: 18,
          last_seen_at: '2026-08-20T12:00:00.000Z',
          comparison: dashboardComparison(18),
        },
      ],
      total_count: 1,
    },
    new_patterns: {
      items: [
        {
          pattern_id: '22222222-2222-4222-8222-222222222222',
          name: 'Rangement terrasse',
          first_seen_at: '2026-08-17T12:00:00.000Z',
        },
        {
          pattern_id: '22222222-2222-4222-8222-222222222223',
          name: 'Bruit extraction',
          first_seen_at: '2026-08-13T12:00:00.000Z',
        },
        {
          pattern_id: '22222222-2222-4222-8222-222222222224',
          name: 'Chariots',
          first_seen_at: '2026-08-10T12:00:00.000Z',
        },
        {
          pattern_id: '22222222-2222-4222-8222-222222222225',
          name: 'Motif 4',
          first_seen_at: '2026-08-16T12:00:00.000Z',
        },
        {
          pattern_id: '22222222-2222-4222-8222-222222222226',
          name: 'Motif 5',
          first_seen_at: '2026-08-16T12:00:00.000Z',
        },
      ],
      total_count: 6,
    },
    locations: {
      items: [
        {
          id: 'cuisine',
          name: 'Cuisine centrale',
          count: 13,
          comparison: dashboardComparison(13),
        },
      ],
      total_count: 1,
    },
    observation_volume: {
      affected: volume(),
      responsible: volume(),
    },
    observation_destinations: {
      waiting: destination(0.12),
      interesting: destination(0.13),
      action_plan_in_progress: destination(0.14),
      resolved_direct: destination(0.34),
      resolved_via_action_plan: destination(0.27),
      resolved_via_resolution_request: destination(0.13),
      canceled: destination(0.12),
    },
    observation_destination_delays: {
      interesting: delay(0.9 * 86400),
      action_plan_in_progress: delay(2.1 * 86400),
      resolved_direct: delay(1.4 * 86400),
      resolved_via_action_plan: delay(1.6 * 86400),
      resolved_via_resolution_request: delay(0.61 * 86400),
      canceled: delay(1.2 * 86400),
    },
    plan_deadline_respect: {
      early: 0.21,
      on_time: 0.54,
      late: 0.25,
      n: 10,
      early_count: 2,
      on_time_count: 5,
      late_count: 3,
      excluded_count: 0,
      early_comparison: dashboardComparison(0.21),
      on_time_comparison: dashboardComparison(0.54, 'complete', -0.03),
      late_comparison: dashboardComparison(0.25, 'complete', -0.02),
    },
    plan_overrun: {
      total_count: 15,
      analyzed_count: 15,
      excluded_count: 0,
      buckets: [
        { key: 'lt_10', count: 3, share: 0.2 },
        { key: 'from_10_to_25', count: 3, share: 0.2 },
        { key: 'from_25_to_50', count: 2, share: 0.18 },
        { key: 'from_50_to_100', count: 4, share: 0.27 },
        { key: 'gte_100', count: 3, share: 0.2 },
      ],
    },
    resolution_quality: {
      n: 25,
      evaluated_count: 25,
      unevaluated_count: 0,
      buckets: [
        { stars: 5, count: 10, share: 0.38 },
        { stars: 4, count: 8, share: 0.31 },
        { stars: 3, count: 4, share: 0.17 },
        { stars: 2, count: 2, share: 0.09 },
        { stars: 1, count: 1, share: 0.05 },
        { stars: 0, count: 0, share: 0 },
      ],
    },
    contributors: [
      {
        user_id: '33333333-3333-4333-8333-333333333333',
        name: 'Nadia B.',
        pts: 24,
        roles: ['staff'],
        poles: ['Cuisine'],
        establishment_names: ['Nord'],
      },
    ],
    ...overrides,
  }
}
