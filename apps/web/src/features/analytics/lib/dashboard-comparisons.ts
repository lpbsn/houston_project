import type { AnalyticsDashboardMetricComparison } from '@/features/analytics/api'

export type DashboardTrendSense = 'positive-up' | 'negative-up' | 'neutral'

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
