import { describe, expect, it } from 'vitest'

import type {
  AnalyticsDashboardMetricComparison,
  AnalyticsDashboardResponse,
  AnalyticsDelayStats,
} from '@/features/analytics/api'
import {
  canShowDashboardDelta,
  collectDashboardComparisons,
  contributorInitials,
  dashboardCoverageBannerMessage,
  dashboardNewBadgeTone,
  dashboardPreviousPeriodFooter,
  DASHBOARD_VS_PREVIOUS_PERIOD,
  emptyObservationDelayMessage,
  formatContributorEstablishments,
  formatContributorPoles,
  formatDashboardDurationDelta,
  formatDashboardHistoryDate,
  formatCountedNoun,
  formatLateDeadlineHero,
  formatMeasuredSample,
  formatNewPatternVolume,
  medianDurationHint,
  shouldShowDashboardDelayMean,
  shouldShowDashboardDelayP90,
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
    undatable_in_scope: 0,
    unstarted_in_scope: 0,
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
    closure_measured_resolved_count: 0,
    closure_measured_canceled_count: 0,
    undatable_signal_terminals: { canceled: 0, resolved: 0, archived: 0 },
    undatable_execution_terminals: { canceled: 0, done: 0 },
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
      early_count: 2,
      on_time_count: 5,
      late_count: 3,
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
        hasDisplayableDelta: true,
      }),
    ).toBeNull()
  })

  it('uses cadrage copy when some deltas remain displayable', () => {
    const date = formatDashboardHistoryDate('2026-01-01T00:00:00.000Z')
    expect(
      dashboardCoverageBannerMessage({
        coverage: 'partial',
        historyReliableFrom: '2026-01-01T00:00:00.000Z',
        hasDisplayableDelta: true,
      }),
    ).toBe(
      `Pas encore assez d’historique pour comparer certaines évolutions. Historique fiable depuis le ${date}.`,
    )
    expect(
      dashboardCoverageBannerMessage({
        coverage: 'not_comparable',
        historyReliableFrom: '2026-01-01T00:00:00.000Z',
        hasDisplayableDelta: true,
      }),
    ).toBe(
      `Pas encore assez d’historique pour comparer certaines évolutions. Historique fiable depuis le ${date}.`,
    )
  })

  it('uses previous-period copy when no delta is displayable', () => {
    const date = formatDashboardHistoryDate('2026-03-15T00:00:00.000Z')
    expect(
      dashboardCoverageBannerMessage({
        coverage: 'not_comparable',
        historyReliableFrom: '2026-03-15T00:00:00.000Z',
        hasDisplayableDelta: false,
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

describe('dashboardPreviousPeriodFooter', () => {
  it('keeps the footer only when a card has a displayable comparison', () => {
    expect(dashboardPreviousPeriodFooter([comparison('complete')])).toBe(
      DASHBOARD_VS_PREVIOUS_PERIOD,
    )
    expect(dashboardPreviousPeriodFooter([comparison('partial'), comparison('not_comparable')])).toBe(
      undefined,
    )
  })
})

describe('dashboardNewBadgeTone', () => {
  it('keeps Nouveau visually neutral on zones and poles', () => {
    expect(dashboardNewBadgeTone('neutral')).toBe('neutral')
    expect(dashboardNewBadgeTone('negative-up')).toBe('positive')
    expect(dashboardNewBadgeTone('positive-up')).toBe('positive')
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

describe('formatNewPatternVolume', () => {
  it('pluralizes Cross observation and establishment counts', () => {
    expect(
      formatNewPatternVolume({ isCross: true, observationCount: 4, establishmentCount: 1 }),
    ).toBe('4 observations · 1 établissement')
    expect(
      formatNewPatternVolume({ isCross: true, observationCount: 1, establishmentCount: 2 }),
    ).toBe('1 observation · 2 établissements')
  })

  it('uses detection copy on an establishment dashboard', () => {
    expect(
      formatNewPatternVolume({ isCross: false, observationCount: 1, establishmentCount: 1 }),
    ).toBe('1 observation depuis sa détection')
    expect(
      formatNewPatternVolume({ isCross: false, observationCount: 3, establishmentCount: 1 }),
    ).toBe('3 observations depuis sa détection')
  })
})

describe('duration visibility and absolute delta', () => {
  it('hides mean and P90 until the sample is large enough', () => {
    expect(shouldShowDashboardDelayMean(1)).toBe(false)
    expect(shouldShowDashboardDelayMean(2)).toBe(true)
    expect(shouldShowDashboardDelayP90(9)).toBe(false)
    expect(shouldShowDashboardDelayP90(10)).toBe(true)
  })

  it('formats an absolute duration delta without a percent sign', () => {
    expect(formatDashboardDurationDelta(4 * 86400)).toBe('4 j')
    expect(formatDashboardDurationDelta(-4 * 86400)).toBe('4 j')
    expect(formatDashboardDurationDelta(0)).toBe('0 min')
    expect(formatDashboardDurationDelta(null)).toBeNull()
  })
})

describe('deadline and contributor copy', () => {
  it('prefers a count formulation at low volume', () => {
    expect(formatLateDeadlineHero({ lateShare: 1, lateCount: 1, n: 1 })).toBe(
      '1 plan en retard sur 1 mesuré',
    )
    expect(formatLateDeadlineHero({ lateShare: 0.22, lateCount: 8, n: 17 })).toContain(
      'des plans sont en retard',
    )
  })

  it('derives initials and pole overflow from payload fields', () => {
    expect(contributorInitials('Nadia B.')).toBe('NB')
    expect(contributorInitials('Léa Martin')).toBe('LM')
    expect(formatContributorPoles([])).toBe('Sans pôle')
    expect(formatContributorPoles(['Cuisine', 'Bar', 'Salle'])).toBe('Cuisine · +2 pôles')
    expect(formatContributorEstablishments([])).toBe('')
    expect(formatContributorEstablishments(['ANBU'])).toBe('ANBU')
    expect(formatContributorEstablishments(['ANBU', 'AKATSUKI'])).toBe('ANBU · AKATSUKI')
    expect(formatContributorEstablishments(['ANBU', 'AKATSUKI', 'Konoha'])).toBe(
      'ANBU · +2 établissements',
    )
  })
})

describe('formatCountedNoun', () => {
  it('does not render NaN when a count is missing', () => {
    expect(formatCountedNoun(Number.NaN, 'plan en retard', 'plans en retard')).toBe(
      '— plans en retard',
    )
  })
})

describe('empty delay copy', () => {
  it('distinguishes a measured empty period from undatable terminal stock', () => {
    expect(emptyObservationDelayMessage('canceled')).toBe(
      'Aucune annulation mesurée sur la période',
    )
    expect(emptyObservationDelayMessage('canceled', 24)).toBe(
      '24 observations annulées dans ce périmètre, sans date historisée. Elles ne peuvent pas entrer dans cette métrique.',
    )
    expect(emptyObservationDelayMessage('resolved')).toBe(
      'Aucune résolution mesurée sur la période',
    )
    expect(emptyObservationDelayMessage('transformed')).toBe(
      'Aucune observation mise en plan sur la période',
    )
  })

  it('keeps the median hint oriented to the duration', () => {
    expect(medianDurationHint('1,8 j')).toBe('La moitié des cas en 1,8 j ou moins')
  })
})
