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
  emptyObservationDelayMessage,
  observationTransformDelayHint,
  canonicalRoutingVolumeHint,
  formatAbsentPreviousPeriodLabel,
  formatAgingBucketLabel,
  formatContributorEstablishments,
  formatContributorPoles,
  formatDashboardDurationDelta,
  formatDashboardHistoryDate,
  formatDashboardPeriodSubtitle,
  formatDashboardPointsDelta,
  formatCountedNoun,
  formatLateCountOnMeasured,
  formatLateDeadlineHero,
  formatMeasuredSample,
  formatNewPatternVolume,
  longTailDurationHint,
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
    locations: [],
    locations_preview_limit: 7,
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

  it('uses UX copy when some deltas remain displayable', () => {
    const date = formatDashboardHistoryDate('2026-01-01T00:00:00.000Z')
    expect(
      dashboardCoverageBannerMessage({
        coverage: 'partial',
        historyReliableFrom: '2026-01-01T00:00:00.000Z',
        hasDisplayableDelta: true,
      }),
    ).toBe(
      `Certaines comparaisons ne sont pas encore disponibles. Données comparables depuis le ${date}.`,
    )
    expect(
      dashboardCoverageBannerMessage({
        coverage: 'not_comparable',
        historyReliableFrom: '2026-01-01T00:00:00.000Z',
        hasDisplayableDelta: true,
      }),
    ).toBe(
      `Certaines comparaisons ne sont pas encore disponibles. Données comparables depuis le ${date}.`,
    )
  })

  it('uses unavailable copy when no delta is displayable', () => {
    const date = formatDashboardHistoryDate('2026-03-15T00:00:00.000Z')
    expect(
      dashboardCoverageBannerMessage({
        coverage: 'not_comparable',
        historyReliableFrom: '2026-03-15T00:00:00.000Z',
        hasDisplayableDelta: false,
      }),
    ).toBe(
      `Comparaison indisponible pour cette période. Données comparables depuis le ${date}.`,
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

describe('period and absence copy', () => {
  it('interpolates the rolling window subtitle', () => {
    expect(formatDashboardPeriodSubtitle(7)).toBe(
      '7 derniers jours · jusqu’à maintenant · comparé aux 7 jours précédents',
    )
    expect(formatDashboardPeriodSubtitle(30)).toBe(
      '30 derniers jours · jusqu’à maintenant · comparé aux 30 jours précédents',
    )
  })

  it('labels a first appearance versus the previous window', () => {
    expect(formatAbsentPreviousPeriodLabel(7)).toBe('Absent des 7 jours précédents')
    expect(formatAbsentPreviousPeriodLabel(15)).toBe('Absent des 15 jours précédents')
  })
})

describe('dashboardNewBadgeTone', () => {
  it('keeps Nouveau visually neutral on locations and poles', () => {
    expect(dashboardNewBadgeTone('neutral')).toBe('neutral')
    expect(dashboardNewBadgeTone('negative-up')).toBe('positive')
    expect(dashboardNewBadgeTone('positive-up')).toBe('positive')
  })
})

describe('formatMeasuredSample', () => {
  it('pluralizes observations and plans without lab jargon', () => {
    expect(formatMeasuredSample(0)).toBe('sur 0 observations')
    expect(formatMeasuredSample(1)).toBe('sur 1 observation')
    expect(formatMeasuredSample(12)).toBe('sur 12 observations')
    expect(formatMeasuredSample(1, 'plan')).toBe('sur 1 plan')
    expect(formatMeasuredSample(3, 'plan')).toBe('sur 3 plans')
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
    ).toBe('1 observation depuis ce premier signalement')
    expect(
      formatNewPatternVolume({ isCross: false, observationCount: 3, establishmentCount: 1 }),
    ).toBe('3 observations depuis ce premier signalement')
  })
})

describe('duration visibility and absolute delta', () => {
  it('hides mean and P90 until the sample is large enough', () => {
    expect(shouldShowDashboardDelayMean(1)).toBe(false)
    expect(shouldShowDashboardDelayMean(2)).toBe(true)
    expect(shouldShowDashboardDelayP90(9)).toBe(false)
    expect(shouldShowDashboardDelayP90(10)).toBe(true)
  })

  it('formats a signed duration delta against the previous window', () => {
    expect(formatDashboardDurationDelta(4 * 86400, 7)).toBe('+4 j vs 7 j d’avant')
    expect(formatDashboardDurationDelta(-4 * 86400, 7)).toBe('-4 j vs 7 j d’avant')
    expect(formatDashboardDurationDelta(0, 7)).toBe('0 min vs 7 j d’avant')
    expect(formatDashboardDurationDelta(null, 7)).toBeNull()
  })

  it('formats rate deltas in points against the previous window', () => {
    expect(formatDashboardPointsDelta(0.07, 7)).toBe('+7 points vs 7 j d’avant')
    expect(formatDashboardPointsDelta(-0.07, 30)).toBe('-7 points vs 30 j d’avant')
  })

  it('states the long-tail duration without P90', () => {
    expect(longTailDurationHint('12 j')).toBe('9 sur 10 en 12 j ou moins')
  })
})

describe('deadline and contributor copy', () => {
  it('prefers a count formulation at low volume', () => {
    expect(formatLateDeadlineHero({ lateShare: 1, lateCount: 1, n: 1 })).toBe(
      '1 en retard sur 1 concerné',
    )
    expect(formatLateCountOnMeasured(3, 17)).toBe('3 sur 17 déjà dus ou terminés')
    expect(formatLateDeadlineHero({ lateShare: 0.22, lateCount: 8, n: 17 })).toMatch(/22\s*% en retard/)
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
    expect(emptyObservationDelayMessage('canceled')).toBe('Aucune annulation sur la période')
    expect(emptyObservationDelayMessage('canceled', 24)).toBe(
      '24 observations annulées, sans date fiable.',
    )
    expect(emptyObservationDelayMessage('resolved')).toBe('Aucune résolution sur la période')
    expect(emptyObservationDelayMessage('transformed')).toBe(
      'Aucune observation mise en plan sur la période',
    )
  })

  it('states first association and live routing as independent of exclusive outcomes', () => {
    expect(observationTransformDelayHint()).toBe(
      'Jusqu’au premier plan. La même observation peut ensuite être résolue ou annulée.',
    )
    expect(canonicalRoutingVolumeHint()).toBe(
      'Si on reclasse un sujet, il change aussi de pôle sur les périodes passées.',
    )
  })

  it('keeps the median hint oriented to the duration', () => {
    expect(medianDurationHint('1,8 j')).toBe('La moitié des cas en 1,8 j ou moins.')
  })
})

describe('formatAgingBucketLabel', () => {
  it('maps backend bucket keys to full-day labels', () => {
    expect(formatAgingBucketLabel({ key: 'lt_3d', label: '< 3 j' })).toBe('Moins de 3 jours')
    expect(formatAgingBucketLabel({ key: '3–7 j', label: '3–7 j' })).toBe('3 à 7 jours')
    expect(formatAgingBucketLabel({ key: '8–15 j', label: '8–15 j' })).toBe('8 à 15 jours')
    expect(formatAgingBucketLabel({ key: 'gt_15d', label: '> 15 j' })).toBe('Plus de 15 jours')
  })
})
