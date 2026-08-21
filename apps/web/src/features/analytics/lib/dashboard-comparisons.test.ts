import { describe, expect, it } from 'vitest'

import type {
  AnalyticsDashboardMetricComparison,
  AnalyticsDashboardResponse,
  AnalyticsDelayStats,
} from '@/features/analytics/api'
import {
  canShowDashboardDelta,
  collectDashboardComparisons,
  dashboardCoverageBannerMessage,
  emptyObservationDelayMessage,
  formatDashboardHistoryDate,
  formatMeasuredSample,
  medianDurationHint,
  worstDashboardCoverage,
} from '@/features/analytics/lib/dashboard-comparisons'

function comparison(
  coverage: AnalyticsDashboardMetricComparison['coverage'] = 'complete',
): AnalyticsDashboardMetricComparison {
  return {
    current_value: 1,
    previous_value: 1,
    absolute_delta: 0,
    relative_change: 0,
    relative_change_status: coverage === 'complete' ? 'computed' : 'not_applicable',
    coverage,
  }
}

function delay(coverage: AnalyticsDashboardMetricComparison['coverage'] = 'complete'): AnalyticsDelayStats {
  return {
    median_seconds: 86400,
    mean_seconds: 86400,
    p90_seconds: null,
    n: 1,
    comparison: comparison(coverage),
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
    establishment_ids: [],
    recurring_patterns: [],
    new_patterns: [],
    new_patterns_preview_limit: 5,
    contributors: [],
    observation_delay_canceled: delay(),
    observation_delay_resolved: delay(),
    observation_delay_transformed: delay(),
    operational_resolution_rate: comparison(),
    closure_resolved_share: comparison(),
    reopenings: comparison(),
    open_observation_count: 0,
    aging_buckets: [],
    aging_over_15d_share: comparison(),
    plan_delay_canceled: delay(),
    plan_delay_resolved: delay(),
    plan_validation: delay(),
    plan_deadlines: {
      early: 0.2,
      on_time: 0.5,
      late: 0.3,
      n: 10,
      early_comparison: comparison(),
      on_time_comparison: comparison(),
      late_comparison: comparison(),
    },
    zones: [],
    zones_preview_limit: 7,
    poles: [],
    ...overrides,
  }
}

describe('worstDashboardCoverage', () => {
  it('returns complete when every comparison is complete', () => {
    expect(worstDashboardCoverage([comparison(), comparison('complete')])).toBe('complete')
    expect(worstDashboardCoverage([])).toBe('complete')
  })

  it('treats not_comparable as worse than partial', () => {
    expect(
      worstDashboardCoverage([comparison('complete'), comparison('partial'), comparison('not_comparable')]),
    ).toBe('not_comparable')
    expect(worstDashboardCoverage([comparison('complete'), comparison('partial')])).toBe('partial')
  })
})

describe('dashboardCoverageBannerMessage', () => {
  it('hides the banner when coverage is complete', () => {
    expect(
      dashboardCoverageBannerMessage({
        coverage: 'complete',
        historyReliableFrom: '2026-01-01T00:00:00.000Z',
      }),
    ).toBeNull()
  })

  it('dates a partial-history banner from history_reliable_from', () => {
    const date = formatDashboardHistoryDate('2026-01-01T00:00:00.000Z')
    expect(
      dashboardCoverageBannerMessage({
        coverage: 'partial',
        historyReliableFrom: '2026-01-01T00:00:00.000Z',
      }),
    ).toBe(`Les évolutions ne portent que sur l’historique fiable, à partir du ${date}.`)
  })

  it('uses not_comparable copy without inventing a coverage rule', () => {
    const date = formatDashboardHistoryDate('2026-03-15T00:00:00.000Z')
    expect(
      dashboardCoverageBannerMessage({
        coverage: 'not_comparable',
        historyReliableFrom: '2026-03-15T00:00:00.000Z',
      }),
    ).toBe(
      `Pas encore assez d’historique pour comparer à la période précédente. Historique fiable à partir du ${date}.`,
    )
  })
})

describe('collectDashboardComparisons', () => {
  it('aggregates backend coverage values already present on the payload', () => {
    const data = dashboard({
      aging_over_15d_share: comparison('partial'),
      recurring_patterns: [
        {
          pattern_id: '11111111-1111-4111-8111-111111111111',
          name: 'Chaîne du froid',
          signal_count: 2,
          comparison: comparison('not_comparable'),
        },
      ],
    })
    expect(worstDashboardCoverage(collectDashboardComparisons(data))).toBe('not_comparable')
  })
})

describe('canShowDashboardDelta', () => {
  it('shows a delta only when coverage is complete', () => {
    expect(canShowDashboardDelta(comparison('complete'))).toBe(true)
    expect(canShowDashboardDelta(comparison('partial'))).toBe(false)
    expect(canShowDashboardDelta(comparison('not_comparable'))).toBe(false)
  })
})

describe('formatMeasuredSample', () => {
  it('pluralizes observations and plans', () => {
    expect(formatMeasuredSample(0)).toBe('0 observations mesurées')
    expect(formatMeasuredSample(1)).toBe('1 observation mesurée')
    expect(formatMeasuredSample(12)).toBe('12 observations mesurées')
    expect(formatMeasuredSample(1, 'plan')).toBe('1 plan mesuré')
    expect(formatMeasuredSample(3, 'plan')).toBe('3 plans mesurés')
  })
})

describe('empty delay copy', () => {
  it('distinguishes a zero sample from missing history', () => {
    expect(emptyObservationDelayMessage('canceled')).toBe(
      'Aucune observation annulée sur la période',
    )
    expect(emptyObservationDelayMessage('resolved')).toBe(
      'Aucune observation résolue sur la période',
    )
    expect(emptyObservationDelayMessage('transformed')).toBe(
      'Aucune observation mise en plan sur la période',
    )
  })

  it('keeps the median hint oriented to the duration', () => {
    expect(medianDurationHint('1,8 j')).toBe('La moitié des cas en 1,8 j ou moins')
  })
})
