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

const DASHBOARD_LOW_VOLUME_DEADLINE_N = 5

export function formatDashboardPeriodSubtitle(days: number): string {
  return `${days} derniers jours · jusqu’à maintenant · comparé aux ${days} jours précédents`
}

export function formatAbsentPreviousPeriodLabel(days: number): string {
  return `Absent des ${days} jours précédents`
}

export function formatVsPreviousPeriod(days: number): string {
  return `vs ${days} j d’avant`
}

export function canShowDashboardDelta(
  comparison: Pick<AnalyticsDashboardMetricComparison, 'coverage' | 'relative_change_status'>,
): boolean {
  return (
    comparison.coverage === 'complete' &&
    (comparison.relative_change_status === 'computed' ||
      comparison.relative_change_status === 'undefined_previous_zero')
  )
}

export function dashboardNewBadgeTone(
  sense: DashboardTrendSense,
): 'positive' | 'neutral' {
  return sense === 'neutral' ? 'neutral' : 'positive'
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

export function formatDashboardPointsDelta(
  value: number | null,
  days: number,
): string | null {
  if (value == null) {
    return null
  }
  const points = value * 100
  const formatted = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(
    Math.abs(points),
  )
  const vs = formatVsPreviousPeriod(days)
  if (points > 0) {
    return `+${formatted} points ${vs}`
  }
  if (points < 0) {
    return `-${formatted} points ${vs}`
  }
  return `${formatted} points ${vs}`
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
  if (seconds === 0) {
    return '0 min'
  }
  if (Math.abs(seconds) < 3600) {
    return `${Math.max(1, Math.round(Math.abs(seconds) / 60))} min`
  }
  const abs = Math.abs(seconds)
  const days = abs / 86400
  if (days < 1) {
    return `${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 }).format(abs / 3600)} h`
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
    ...data.locations.map((item) => item.comparison),
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
  hasDisplayableDelta: boolean
}): string | null {
  if (options.coverage === 'complete') {
    return null
  }
  const date = formatDashboardHistoryDate(options.historyReliableFrom)
  if (options.hasDisplayableDelta) {
    return `Certaines comparaisons ne sont pas encore disponibles. Données comparables depuis le ${date}.`
  }
  return `Comparaison indisponible pour cette période. Données comparables depuis le ${date}.`
}

export function formatMeasuredSample(
  n: number,
  unit: 'observation' | 'plan' = 'observation',
): string {
  if (unit === 'plan') {
    return n === 1 ? 'sur 1 plan' : `sur ${new Intl.NumberFormat('fr-FR').format(n)} plans`
  }
  return n === 1
    ? 'sur 1 observation'
    : `sur ${new Intl.NumberFormat('fr-FR').format(n)} observations`
}

export function medianDurationHint(durationLabel: string): string {
  return `La moitié des cas en ${durationLabel} ou moins.`
}

export function longTailDurationHint(durationLabel: string): string {
  return `9 sur 10 en ${durationLabel} ou moins`
}

export function observationTransformDelayHint(): string {
  return 'Jusqu’au premier plan. La même observation peut ensuite être résolue ou annulée.'
}

export function observationCancellationDelayHint(): string {
  return 'Temps jusqu’à l’annulation. Ce n’est pas un jugement de qualité.'
}

export function canonicalRoutingVolumeHint(): string {
  return 'Si on reclasse un sujet, il change aussi de pôle sur les périodes passées.'
}

export function newPatternsVolumeTooltip(): string {
  return 'Le volume compte depuis la première fois que ce sujet a été vu, pas seulement sur la période affichée.'
}

export function resolutionStripTooltip(): string {
  return 'Parmi les observations déjà résolues sur la période, pas le temps d’attente actuel.'
}

export function planDeadlinesStripTooltip(): string {
  return 'Uniquement les plans déjà dus ou déjà terminés. Ceux encore dans les délais ne sont pas comptés.'
}

export function planDeadlinesDenominatorCopy(): string {
  return 'Parmi les plans déjà dus ou déjà terminés. Les plans encore dans les délais ne sont pas comptés.'
}

export function operationalResolutionRateHint(): string {
  return 'Des sujets à traiter sur la période, ceux qui sont résolus maintenant.'
}

export function reopeningsHint(): string {
  return 'Résolues puis rouvertes sur la période.'
}

export function emptyObservationDelayMessage(
  kind: 'canceled' | 'resolved' | 'transformed',
  undatableInScope = 0,
): string {
  if (kind === 'transformed') {
    return 'Aucune observation mise en plan sur la période'
  }
  if (undatableInScope > 0) {
    const stock = formatCountedNoun(
      undatableInScope,
      kind === 'canceled' ? 'observation annulée' : 'observation résolue',
      kind === 'canceled' ? 'observations annulées' : 'observations résolues',
    )
    return `${stock}, sans date fiable.`
  }
  if (kind === 'canceled') {
    return 'Aucune annulation sur la période'
  }
  return 'Aucune résolution sur la période'
}

export function emptyPlanDelayMessage(
  kind: 'canceled' | 'resolved' | 'validated',
  options: { undatableInScope?: number; unstartedInScope?: number } = {},
): string {
  const undatable = options.undatableInScope ?? 0
  const unstarted = options.unstartedInScope ?? 0
  if (kind === 'canceled' && undatable > 0) {
    const stock = formatCountedNoun(undatable, 'plan annulé', 'plans annulés')
    return `${stock}, sans date fiable.`
  }
  if (kind === 'canceled' && unstarted > 0) {
    return 'Des plans ont été annulés avant d’être démarrés ; ils n’entrent pas dans ce délai.'
  }
  if (kind === 'resolved' && undatable > 0) {
    const stock = formatCountedNoun(undatable, 'plan résolu', 'plans résolus')
    return `${stock}, sans date fiable.`
  }
  if (kind === 'validated' && undatable > 0) {
    return emptyPlanDelayMessage('resolved', { undatableInScope: undatable })
  }
  if (kind === 'canceled') {
    return 'Aucune annulation de plan sur la période'
  }
  if (kind === 'resolved') {
    return 'Aucune résolution de plan sur la période'
  }
  return 'Aucune validation sur la période'
}

export function delayExclusionNote(
  undatableInScope: number,
  _unit: 'observation' | 'plan' = 'observation',
): string | null {
  if (undatableInScope <= 0) {
    return null
  }
  const stock = formatCountedNoun(
    undatableInScope,
    'dossier sans date fiable, non inclus',
    'dossiers sans date fiable, non inclus',
  )
  return stock
}

export function closureResolvedShareHint(options: {
  measuredResolvedCount: number
  measuredCanceledCount: number
  undatableResolved: number
  undatableCanceled: number
}): string {
  const undatable = options.undatableResolved + options.undatableCanceled
  if (undatable > 0) {
    const excluded = delayExclusionNote(undatable) ?? ''
    const measured = options.measuredResolvedCount + options.measuredCanceledCount
    if (measured === 0) {
      return `${excluded} ; aucun dossier fermé mesurable sur la période.`
    }
    return `Parmi les dossiers fermés sur la période. Le stock ouvert n’entre pas. ${excluded}.`
  }
  return 'Parmi les dossiers fermés sur la période. Le stock ouvert n’entre pas.'
}

export function formatDashboardDurationDelta(
  seconds: number | null,
  days: number,
): string | null {
  if (seconds == null) {
    return null
  }
  const duration = formatDashboardDuration(Math.abs(seconds))
  const vs = formatVsPreviousPeriod(days)
  if (seconds > 0) {
    return `+${duration} ${vs}`
  }
  if (seconds < 0) {
    return `-${duration} ${vs}`
  }
  return `${duration} ${vs}`
}

export function shouldShowDashboardDelayMean(n: number): boolean {
  return n >= 2
}

export function shouldShowDashboardDelayP90(n: number): boolean {
  return n >= 10
}

export function formatCountedNoun(count: number, singular: string, plural: string): string {
  if (!Number.isFinite(count)) {
    return `— ${plural}`
  }
  const formatted = new Intl.NumberFormat('fr-FR').format(count)
  return `${formatted} ${count === 1 ? singular : plural}`
}

export function formatDashboardObservationCount(count: number): string {
  return formatCountedNoun(count, 'observation', 'observations')
}

export function formatNewPatternVolume(options: {
  isCross: boolean
  observationCount: number
  establishmentCount: number | null
}): string {
  const observations = formatDashboardObservationCount(options.observationCount)
  if (!options.isCross) {
    return options.observationCount === 1
      ? '1 observation depuis ce premier signalement'
      : `${observations} depuis ce premier signalement`
  }
  const establishments = formatCountedNoun(
    options.establishmentCount ?? 0,
    'établissement',
    'établissements',
  )
  return `${observations} · ${establishments}`
}

export function contributorInitials(name: string): string {
  const parts = name
    .trim()
    .split(/\s+/)
    .map((part) => part.replace(/[^\p{L}\p{N}]/gu, ''))
    .filter(Boolean)
  if (parts.length === 0) {
    return '?'
  }
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase()
  }
  const first = parts[0][0] ?? ''
  const last = parts[parts.length - 1]?.[0] ?? ''
  return `${first}${last}`.toUpperCase()
}

export function formatContributorPoles(poles: string[]): string {
  if (poles.length === 0) {
    return 'Sans pôle'
  }
  if (poles.length === 1) {
    return poles[0] ?? 'Sans pôle'
  }
  const extra = poles.length - 1
  return `${poles[0]} · +${extra} ${extra === 1 ? 'pôle' : 'pôles'}`
}

export function formatContributorEstablishments(names: string[]): string {
  if (names.length === 0) {
    return ''
  }
  if (names.length === 1) {
    return names[0] ?? ''
  }
  if (names.length === 2) {
    return `${names[0]} · ${names[1]}`
  }
  const extra = names.length - 1
  return `${names[0]} · +${extra} établissements`
}

export function formatLateDeadlineHero(options: {
  lateShare: number | null
  lateCount: number
  n: number
}): string {
  if (options.n > 0 && options.n < DASHBOARD_LOW_VOLUME_DEADLINE_N) {
    return formatLateCountOnMeasured(options.lateCount, options.n)
  }
  return `${formatDashboardPercent(options.lateShare)} en retard`
}

export function formatLateCountOnMeasured(lateCount: number, n: number): string {
  if (n > 0 && n < DASHBOARD_LOW_VOLUME_DEADLINE_N) {
    return `${formatCountedNoun(lateCount, 'en retard', 'en retard')} sur ${
      n === 1 ? '1 concerné' : `${new Intl.NumberFormat('fr-FR').format(n)} concernés`
    }`
  }
  return `${new Intl.NumberFormat('fr-FR').format(lateCount)} sur ${new Intl.NumberFormat(
    'fr-FR',
  ).format(n)} déjà dus ou terminés`
}

export function formatAgingBucketLabel(bucket: { key: string; label: string }): string {
  const token = `${bucket.key} ${bucket.label}`
  if (
    bucket.key === 'lt_3d' ||
    bucket.key === '< 3 j' ||
    bucket.label === '< 3 j' ||
    token.includes('< 3')
  ) {
    return 'Moins de 3 jours'
  }
  if (
    bucket.key === '3–7 j' ||
    bucket.label === '3–7 j' ||
    token.includes('3–7') ||
    token.includes('3-7')
  ) {
    return '3 à 7 jours'
  }
  if (
    bucket.key === '8–15 j' ||
    bucket.label === '8–15 j' ||
    token.includes('8–15') ||
    token.includes('8-15')
  ) {
    return '8 à 15 jours'
  }
  if (isOver15dAgingBucket(bucket)) {
    return 'Plus de 15 jours'
  }
  return bucket.label
}

export function isOver15dAgingBucket(bucket: { key: string; label: string }): boolean {
  return bucket.key === '> 15 j' || bucket.key === 'gt_15d' || bucket.label.includes('> 15')
}
