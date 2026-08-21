import type {
  AnalyticsDashboardMetricComparison,
  AnalyticsDashboardResponse,
} from '@/features/analytics/api'

export type DashboardTrendSense = 'positive-up' | 'negative-up' | 'neutral'
export type DashboardCoverage = AnalyticsDashboardMetricComparison['coverage']

const COVERAGE_SEVERITY: Record<DashboardCoverage, number> = {
  complete: 0,
  partial: 1,
  not_comparable: 2,
}

export const DASHBOARD_VS_PREVIOUS_PERIOD = 'VS PÉRIODE PRÉCÉDENTE'
export const DASHBOARD_INSUFFICIENT_P90_COPY =
  'Pas assez de cas pour estimer les délais longs'

export function canShowDashboardDelta(
  comparison: Pick<AnalyticsDashboardMetricComparison, 'coverage' | 'relative_change_status'>,
): boolean {
  return (
    comparison.coverage === 'complete' &&
    (comparison.relative_change_status === 'computed' ||
      comparison.relative_change_status === 'undefined_previous_zero')
  )
}

export function dashboardTrendTone(
  delta: number | null,
  sense: DashboardTrendSense,
): 'positive' | 'negative' | 'neutral' | 'new' {
  if (delta == null) {
    return 'neutral'
  }
  if (delta === 0) {
    return 'neutral'
  }
  if (sense === 'neutral') {
    return 'neutral'
  }
  const upIsPositive = sense === 'positive-up'
  if (delta > 0) {
    return upIsPositive ? 'positive' : 'negative'
  }
  return upIsPositive ? 'negative' : 'positive'
}

export function formatDashboardPercentDelta(value: number | null): string | null {
  if (value == null) {
    return null
  }
  const percent = value * 100
  const formatted = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(
    Math.abs(percent),
  )
  if (percent > 0) {
    return `+${formatted} %`
  }
  if (percent < 0) {
    return `-${formatted} %`
  }
  return `${formatted} %`
}

export function formatDashboardPointsDelta(value: number | null): string | null {
  if (value == null) {
    return null
  }
  const points = value * 100
  const formatted = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(
    Math.abs(points),
  )
  if (points > 0) {
    return `+${formatted} pts`
  }
  if (points < 0) {
    return `-${formatted} pts`
  }
  return `${formatted} pts`
}

export function formatDashboardCountDelta(value: number | null): string | null {
  if (value == null) {
    return null
  }
  const formatted = new Intl.NumberFormat('fr-FR').format(Math.abs(value))
  if (value > 0) {
    return `+${formatted}`
  }
  if (value < 0) {
    return `-${formatted}`
  }
  return formatted
}

export function formatDashboardDuration(seconds: number | null): string {
  if (seconds == null) {
    return '—'
  }
  if (seconds < 3600) {
    return `${Math.max(1, Math.round(seconds / 60))} min`
  }
  const days = seconds / 86400
  if (days < 1) {
    return `${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 }).format(seconds / 3600)} h`
  }
  return `${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 }).format(days)} j`
}

export function formatDashboardPercent(value: number | null): string {
  if (value == null) {
    return '—'
  }
  return new Intl.NumberFormat('fr-FR', {
    maximumFractionDigits: 0,
    style: 'percent',
  }).format(value)
}

export function formatRelativeDaysAgo(isoDate: string, now = new Date()): string {
  const then = new Date(isoDate)
  const diffMs = Math.max(0, now.getTime() - then.getTime())
  const days = Math.floor(diffMs / 86400000)
  if (days <= 0) {
    return "Détecté aujourd'hui"
  }
  if (days === 1) {
    return 'Détecté il y a 1 j'
  }
  return `Détecté il y a ${days} j`
}

export function dashboardNewLabel(
  comparison: Pick<AnalyticsDashboardMetricComparison, 'relative_change_status' | 'coverage'>,
): boolean {
  return (
    comparison.coverage === 'complete' &&
    comparison.relative_change_status === 'undefined_previous_zero'
  )
}

export function worstDashboardCoverage(
  comparisons: Array<Pick<AnalyticsDashboardMetricComparison, 'coverage'>>,
): DashboardCoverage {
  let worst: DashboardCoverage = 'complete'
  for (const comparison of comparisons) {
    if (COVERAGE_SEVERITY[comparison.coverage] > COVERAGE_SEVERITY[worst]) {
      worst = comparison.coverage
    }
  }
  return worst
}

export function collectDashboardComparisons(
  data: AnalyticsDashboardResponse,
): AnalyticsDashboardMetricComparison[] {
  return [
    data.operational_resolution_rate,
    data.closure_resolved_share,
    data.reopenings,
    data.aging_over_15d_share,
    data.observation_delay_canceled.comparison,
    data.observation_delay_resolved.comparison,
    data.observation_delay_transformed.comparison,
    data.plan_delay_canceled.comparison,
    data.plan_delay_resolved.comparison,
    data.plan_validation.comparison,
    data.plan_deadlines.early_comparison,
    data.plan_deadlines.on_time_comparison,
    data.plan_deadlines.late_comparison,
    ...data.recurring_patterns.map((item) => item.comparison),
    ...data.zones.map((item) => item.comparison),
    ...data.poles.map((item) => item.comparison),
  ]
}

export function formatDashboardHistoryDate(isoDate: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(isoDate))
}

export function dashboardCoverageBannerMessage(options: {
  coverage: DashboardCoverage
  historyReliableFrom: string
}): string | null {
  if (options.coverage === 'complete') {
    return null
  }
  const date = formatDashboardHistoryDate(options.historyReliableFrom)
  if (options.coverage === 'not_comparable') {
    return `Pas encore assez d’historique pour comparer à la période précédente. Historique fiable à partir du ${date}.`
  }
  return `Les évolutions ne portent que sur l’historique fiable, à partir du ${date}.`
}

export function formatMeasuredSample(
  n: number,
  unit: 'observation' | 'plan' = 'observation',
): string {
  const formatted = new Intl.NumberFormat('fr-FR').format(n)
  if (unit === 'plan') {
    return n === 1 ? '1 plan mesuré' : `${formatted} plans mesurés`
  }
  return n === 1 ? '1 observation mesurée' : `${formatted} observations mesurées`
}

export function medianDurationHint(durationLabel: string): string {
  return `La moitié des cas en ${durationLabel} ou moins`
}

export function emptyObservationDelayMessage(
  kind: 'canceled' | 'resolved' | 'transformed',
): string {
  if (kind === 'canceled') {
    return 'Aucune observation annulée sur la période'
  }
  if (kind === 'resolved') {
    return 'Aucune observation résolue sur la période'
  }
  return 'Aucune observation mise en plan sur la période'
}

export function emptyPlanDelayMessage(kind: 'canceled' | 'resolved' | 'validated'): string {
  if (kind === 'canceled') {
    return 'Aucun plan annulé sur la période'
  }
  if (kind === 'resolved') {
    return 'Aucun plan résolu sur la période'
  }
  return 'Aucune validation sur la période'
}
