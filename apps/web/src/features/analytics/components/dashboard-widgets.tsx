import { useState, type ReactNode } from 'react'
import { ArrowDownRight, ArrowUpRight, Download } from 'lucide-react'

import type {
  AnalyticsContributorItem,
  AnalyticsDashboardMetricComparison,
  AnalyticsDashboardResponse,
  AnalyticsDelayStats,
  AnalyticsNamedCountItem,
  AnalyticsNewPatternItem,
  AnalyticsRecurringPatternItem,
} from '@/features/analytics/api'
import {
  canShowDashboardDelta,
  contributorInitials,
  dashboardNewBadgeTone,
  dashboardNewLabel,
  dashboardTrendTone,
  emptyObservationDelayMessage,
  emptyPlanDelayMessage,
  observationCancellationDelayHint,
  observationTransformDelayHint,
  canonicalRoutingVolumeHint,
  closureResolvedShareHint,
  delayExclusionNote,
  formatAgingBucketLabel,
  formatContributorEstablishments,
  formatContributorPoles,
  formatCountedNoun,
  formatDashboardCountDelta,
  formatDashboardDuration,
  formatDashboardDurationDelta,
  formatDashboardObservationCount,
  formatDashboardPercent,
  formatDashboardPercentDelta,
  formatDashboardPointsDelta,
  formatAbsentPreviousPeriodLabel,
  formatLateCountOnMeasured,
  formatMeasuredSample,
  formatNewPatternVolume,
  formatRelativeDaysAgo,
  isOver15dAgingBucket,
  longTailDurationHint,
  medianDurationHint,
  newPatternsVolumeTooltip,
  operationalResolutionRateHint,
  planDeadlinesDenominatorCopy,
  planDeadlinesStripTooltip,
  reopeningsHint,
  resolutionStripTooltip,
  shouldShowDashboardDelayMean,
  shouldShowDashboardDelayP90,
  type DashboardTrendSense,
} from '@/features/analytics/lib/dashboard-comparisons'
import { formatMembershipRoleDisplay } from '@/lib/display-names'
import { cn } from '@/lib/utils'

function DashboardCard({
  title,
  subtitle,
  children,
  className,
  titleTooltip,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
  titleTooltip?: string
}) {
  return (
    <section
      className={cn(
        'flex h-auto min-w-0 max-w-full flex-col rounded-2xl border border-[#E8E6DF] bg-white p-5 lg:p-6',
        className,
      )}
      title={titleTooltip}
    >
      <h2 className="text-base font-semibold tracking-tight text-[#1a1a1a]">{title}</h2>
      {subtitle ? <p className="mt-1 text-[12px] text-[#7D7B75]">{subtitle}</p> : null}
      <div className="mt-4 min-w-0">{children}</div>
    </section>
  )
}

function isDisplayedTrendFlat(
  delta: number | null,
  format: 'percent' | 'points' | 'count' | 'duration',
): boolean {
  if (delta == null) {
    return false
  }
  if (format === 'percent' || format === 'points') {
    return Math.round(Math.abs(delta) * 100) === 0
  }
  return delta === 0
}

export function TrendBadge({
  comparison,
  sense,
  format = 'percent',
  periodDays,
}: {
  comparison: AnalyticsDashboardMetricComparison
  sense: DashboardTrendSense
  format?: 'percent' | 'points' | 'count' | 'duration'
  periodDays: number
}) {
  if (!canShowDashboardDelta(comparison)) {
    return null
  }
  if (dashboardNewLabel(comparison)) {
    const newTone = dashboardNewBadgeTone(sense)
    return (
      <span
        className={cn(
          'text-[12px] font-semibold',
          newTone === 'neutral' ? 'text-[#7D7B75]' : 'text-[#1F7A4D]',
        )}
      >
        {formatAbsentPreviousPeriodLabel(periodDays)}
      </span>
    )
  }
  const delta =
    format === 'points' || format === 'count' || format === 'duration'
      ? comparison.absolute_delta
      : comparison.relative_change
  const label =
    format === 'points'
      ? formatDashboardPointsDelta(comparison.relative_change, periodDays)
      : format === 'count'
        ? formatDashboardCountDelta(comparison.absolute_delta)
        : format === 'duration'
          ? formatDashboardDurationDelta(comparison.absolute_delta, periodDays)
          : formatDashboardPercentDelta(comparison.relative_change)
  if (!label || isDisplayedTrendFlat(delta, format)) {
    return null
  }
  const tone = dashboardTrendTone(delta, sense)
  const Icon = (delta ?? 0) < 0 ? ArrowDownRight : ArrowUpRight
  return (
    <span
      className={cn(
        'inline-flex min-w-0 flex-wrap items-center gap-0.5 text-[12px] font-semibold',
        tone === 'positive' && 'text-[#1F7A4D]',
        tone === 'negative' && 'text-[#E24B4A]',
        tone === 'neutral' && 'text-[#7D7B75]',
      )}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {label}
    </span>
  )
}

type ShareSegment = {
  key: string
  label: string
  value: number | null
  className: string
  count?: number
  comparison?: AnalyticsDashboardMetricComparison
  sense?: DashboardTrendSense
  emphasize?: boolean
}

function StackedShareBar({
  segments,
  periodDays,
}: {
  segments: ShareSegment[]
  periodDays: number
}) {
  return (
    <div className="min-w-0">
      <div className="flex h-3.5 min-w-0 overflow-hidden rounded-full bg-[#F0EFE9]">
        {segments.map((segment) =>
          segment.value && segment.value > 0 ? (
            <span
              key={segment.key}
              className={segment.className}
              style={{ width: `${segment.value * 100}%` }}
            />
          ) : null,
        )}
      </div>
      <ul className="mt-3 flex min-w-0 flex-wrap gap-x-4 gap-y-2">
        {segments.map((segment) => (
          <li
            key={segment.key}
            className={cn(
              'flex min-w-0 flex-wrap items-center gap-1.5 text-[13px] text-[#7D7B75]',
              segment.emphasize && 'font-medium text-[#1a1a1a]',
            )}
          >
            <span>
              {segment.label}{' '}
              <span className="tabular-nums text-[#1a1a1a]">
                {segment.count != null
                  ? `${segment.count} · ${formatDashboardPercent(segment.value)}`
                  : formatDashboardPercent(segment.value)}
              </span>
            </span>
            {segment.comparison && segment.sense ? (
              <TrendBadge
                comparison={segment.comparison}
                sense={segment.sense}
                format="points"
                periodDays={periodDays}
              />
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

function DurationHero({
  label,
  stats,
  sense,
  emptyLabel,
  hint,
  extraHint,
  unit = 'observation',
  periodDays,
}: {
  label: string
  stats: AnalyticsDelayStats
  sense: DashboardTrendSense
  emptyLabel: string
  hint?: string
  extraHint?: string
  unit?: 'observation' | 'plan'
  periodDays: number
}) {
  if (stats.n === 0 || stats.median_seconds == null) {
    return (
      <div className="min-w-0">
        <p className="text-[12px] font-medium text-[#7D7B75]">{label}</p>
        <p className="mt-1 text-sm text-[#7D7B75]">{emptyLabel}</p>
        {hint ? <p className="mt-2 text-[12px] text-[#7D7B75]">{hint}</p> : null}
        {extraHint ? <p className="mt-2 text-[12px] text-[#7D7B75]">{extraHint}</p> : null}
      </div>
    )
  }

  const duration = formatDashboardDuration(stats.median_seconds)
  const showMean = shouldShowDashboardDelayMean(stats.n) && stats.mean_seconds != null
  const showP90 =
    shouldShowDashboardDelayP90(stats.n) && stats.p90_seconds != null
  const sample = formatMeasuredSample(stats.n, unit)
  const exclusion = delayExclusionNote(stats.undatable_in_scope)

  return (
    <div className="min-w-0">
      <p className="text-[12px] font-medium text-[#7D7B75]">{label}</p>
      <p className="mt-1 flex min-w-0 flex-wrap items-baseline gap-2 text-[1.75rem] font-semibold leading-none tabular-nums tracking-tight text-[#1a1a1a] lg:text-[2rem]">
        {duration}
        <TrendBadge
          comparison={stats.comparison}
          sense={sense}
          format="duration"
          periodDays={periodDays}
        />
      </p>
      <p className="mt-2 min-w-0 break-words text-[12px] text-[#7D7B75]">
        {[
          stats.n === 1
            ? `médiane · ${sample}`
            : [
                `médiane · ${sample}`,
                showMean ? `en moyenne ${formatDashboardDuration(stats.mean_seconds)}` : null,
                showP90 ? longTailDurationHint(formatDashboardDuration(stats.p90_seconds)) : null,
              ]
                .filter(Boolean)
                .join(' · '),
          exclusion,
        ]
          .filter(Boolean)
          .join(' · ')}
      </p>
      {hint ? <p className="mt-2 text-[12px] text-[#7D7B75]">{hint}</p> : null}
      {extraHint ? <p className="mt-2 text-[12px] text-[#7D7B75]">{extraHint}</p> : null}
    </div>
  )
}

function CompactDuration({
  label,
  stats,
  sense,
  emptyLabel,
  unit = 'plan',
  periodDays,
}: {
  label: string
  stats: AnalyticsDelayStats
  sense: DashboardTrendSense
  emptyLabel: string
  unit?: 'observation' | 'plan'
  periodDays: number
}) {
  if (stats.n === 0 || stats.median_seconds == null) {
    return (
      <div className="min-w-0">
        <p className="text-[12px] text-[#7D7B75]">{label}</p>
        <p className="mt-0.5 text-[13px] text-[#7D7B75]">{emptyLabel}</p>
      </div>
    )
  }

  const exclusion = delayExclusionNote(stats.undatable_in_scope)

  return (
    <div className="min-w-0">
      <p className="text-[12px] text-[#7D7B75]">{label}</p>
      <p className="mt-0.5 flex min-w-0 flex-wrap items-baseline gap-1.5 text-base font-semibold tabular-nums text-[#1a1a1a]">
        {formatDashboardDuration(stats.median_seconds)}
        <TrendBadge
          comparison={stats.comparison}
          sense={sense}
          format="duration"
          periodDays={periodDays}
        />
        <span className="text-[12px] font-medium text-[#7D7B75]">
          {formatMeasuredSample(stats.n, unit)}
        </span>
      </p>
      {exclusion ? <p className="mt-0.5 text-[12px] text-[#A8A59E]">{exclusion}</p> : null}
    </div>
  )
}

function SecondaryMetric({
  label,
  value,
  comparison,
  sense,
  format,
  hint,
  tooltip,
  periodDays,
}: {
  label: string
  value: string
  comparison: AnalyticsDashboardMetricComparison
  sense: DashboardTrendSense
  format: 'percent' | 'points' | 'count' | 'duration'
  hint?: string
  tooltip?: string
  periodDays: number
}) {
  return (
    <div className="min-w-0" title={tooltip}>
      <p className="text-[12px] font-medium text-[#7D7B75]">{label}</p>
      <p className="mt-1 flex min-w-0 flex-wrap items-baseline gap-2 text-lg font-semibold tabular-nums text-[#1a1a1a]">
        {value}
        <TrendBadge comparison={comparison} sense={sense} format={format} periodDays={periodDays} />
      </p>
      {hint ? <p className="mt-0.5 text-[12px] text-[#A8A59E]">{hint}</p> : null}
    </div>
  )
}

function ComingSoonBadge() {
  return (
    <span className="inline-flex rounded-full bg-[#1a1a1a] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-white">
      Bientôt disponible
    </span>
  )
}

export function DashboardAiSummaryPlaceholder() {
  return (
    <section className="min-w-0 max-w-full rounded-2xl border border-[#E8E6DF] bg-white px-5 py-4">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold tracking-tight text-[#1a1a1a]">Résumé IA</h2>
          <p className="mt-1 text-[13px] text-[#7D7B75]">
            Une synthèse des évolutions et points d’attention sera disponible ici.
          </p>
        </div>
        <ComingSoonBadge />
      </div>
    </section>
  )
}

export function DashboardRevenuePlaceholder() {
  return (
    <section className="min-w-0 max-w-full rounded-2xl border border-[#E8E6DF] bg-white px-5 py-4">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold tracking-tight text-[#1a1a1a]">
            Chiffre d’affaires vs observations
          </h2>
          <p className="mt-1 text-[13px] text-[#7D7B75]">
            Croisement avec les données d’activité à venir.
          </p>
        </div>
        <ComingSoonBadge />
      </div>
    </section>
  )
}

export function DashboardExportButton() {
  return (
    <button
      type="button"
      disabled
      className="inline-flex h-9 min-w-0 items-center gap-2 rounded-lg bg-[#1F7A4D] px-3.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-70"
    >
      <Download className="h-4 w-4" aria-hidden />
      Exporter
      <span className="text-[11px] font-medium opacity-90">Bientôt</span>
    </button>
  )
}

export function OperationalSummaryStrip({
  data,
  periodDays,
}: {
  data: AnalyticsDashboardResponse
  periodDays: number
}) {
  const over15 = data.aging_buckets.find(isOver15dAgingBucket)
  const over15Count = over15?.count ?? 0
  const resolved = data.observation_delay_resolved
  const deadlines = data.plan_deadlines
  const openLabel =
    data.open_observation_count <= 1
      ? 'observation encore ouverte'
      : 'observations encore ouvertes'

  return (
    <section className="grid min-w-0 grid-cols-2 gap-x-4 gap-y-4 rounded-2xl border border-[#E8E6DF] bg-white px-5 py-4 lg:grid-cols-4 lg:gap-6 lg:px-6 lg:py-5">
      <div className="min-w-0">
        <p className="text-[1.75rem] font-semibold leading-none tabular-nums tracking-tight text-[#1a1a1a] lg:text-[2rem]">
          {data.open_observation_count}
        </p>
        <p className="mt-1.5 text-[13px] text-[#7D7B75]">{openLabel}</p>
        <p className="mt-0.5 text-[12px] text-[#A8A59E]">En ce moment</p>
      </div>
      <div className="min-w-0">
        <p className="flex min-w-0 flex-wrap items-baseline gap-1.5 text-[1.75rem] font-semibold leading-none tabular-nums tracking-tight text-[#1a1a1a] lg:text-[2rem]">
          {over15Count}
          {data.open_observation_count > 0 ? (
            <span className="text-base font-semibold text-[#7D7B75]">
              · {formatDashboardPercent(data.aging_over_15d_share.current_value)}
            </span>
          ) : null}
        </p>
        <p className="mt-1.5 text-[13px] text-[#7D7B75]">depuis plus de 15 jours</p>
        {data.open_observation_count > 0 ? (
          <p className="mt-0.5 text-[12px] text-[#A8A59E]">
            parmi les {formatCountedNoun(data.open_observation_count, 'ouverte', 'ouvertes')}
          </p>
        ) : null}
      </div>
      <div className="min-w-0" title={resolutionStripTooltip()}>
        {resolved.n === 0 || resolved.median_seconds == null ? (
          <>
            <p className="text-[1.75rem] font-semibold leading-none text-[#1a1a1a] lg:text-[2rem]">
              —
            </p>
            <p className="mt-1.5 text-[13px] text-[#7D7B75]">
              {emptyObservationDelayMessage('resolved', resolved.undatable_in_scope)}
            </p>
          </>
        ) : (
          <>
            <p className="flex min-w-0 flex-wrap items-baseline gap-2 text-[1.75rem] font-semibold leading-none tabular-nums tracking-tight text-[#1a1a1a] lg:text-[2rem]">
              {formatDashboardDuration(resolved.median_seconds)}
              <TrendBadge
                comparison={resolved.comparison}
                sense="negative-up"
                format="duration"
                periodDays={periodDays}
              />
            </p>
            <p className="mt-1.5 text-[13px] text-[#7D7B75]">
              pour résoudre · médiane
            </p>
            <p className="mt-0.5 text-[12px] text-[#A8A59E]">
              {formatMeasuredSample(resolved.n)} · sur la période
            </p>
          </>
        )}
      </div>
      <div className="min-w-0" title={planDeadlinesStripTooltip()}>
        {deadlines.n === 0 ? (
          <>
            <p className="text-[1.75rem] font-semibold leading-none text-[#1a1a1a] lg:text-[2rem]">
              —
            </p>
            <p className="mt-1.5 text-[13px] text-[#7D7B75]">Aucun plan avec date d’échéance</p>
          </>
        ) : (
          <>
            <p className="flex min-w-0 flex-wrap items-baseline gap-2 text-[1.75rem] font-semibold leading-none tabular-nums tracking-tight text-[#1a1a1a] lg:text-[2rem]">
              {deadlines.n < 5
                ? deadlines.late_count
                : formatDashboardPercent(deadlines.late)}
              <TrendBadge
                comparison={deadlines.late_comparison}
                sense="negative-up"
                format="points"
                periodDays={periodDays}
              />
            </p>
            <p className="mt-1.5 min-w-0 break-words text-[13px] text-[#7D7B75]">
              {deadlines.n < 5
                ? formatLateCountOnMeasured(deadlines.late_count, deadlines.n)
                : `en retard · ${formatLateCountOnMeasured(deadlines.late_count, deadlines.n)}`}
            </p>
          </>
        )}
      </div>
    </section>
  )
}

export function RecurringPatternsCard({
  items,
  isCross,
  periodDays,
}: {
  items: AnalyticsRecurringPatternItem[]
  isCross: boolean
  periodDays: number
}) {
  const max = Math.max(...items.map((item) => item.signal_count), 1)
  const subtitle = isCross
    ? 'Sujets vus au moins 2 fois sur la période · Tous établissements'
    : 'Sujets vus au moins 2 fois sur la période'
  return (
    <DashboardCard title="Motifs récurrents" subtitle={subtitle}>
      {items.length === 0 ? (
        <div>
          <p className="text-sm font-medium text-[#1a1a1a]">Aucun problème récurrent détecté</p>
          <p className="mt-1 text-[13px] text-[#7D7B75]">
            Aucun motif n’apparaît sur plusieurs observations pendant cette période.
          </p>
        </div>
      ) : (
        <ol className="flex flex-col gap-4">
          {items.map((item, index) => (
            <li key={item.pattern_id} className="min-w-0">
              <div className="flex min-w-0 items-baseline justify-between gap-3">
                <span className="min-w-0 truncate text-sm font-medium text-[#1a1a1a]">
                  <span className="mr-2 font-semibold tabular-nums text-[#1F7A4D]">
                    {index + 1}
                  </span>
                  {item.name}
                </span>
                <span className="flex shrink-0 flex-wrap items-center justify-end gap-2 text-sm font-semibold tabular-nums text-[#1a1a1a]">
                  {formatDashboardObservationCount(item.signal_count)}
                  <TrendBadge
                    comparison={item.comparison}
                    sense="negative-up"
                    format="count"
                    periodDays={periodDays}
                  />
                </span>
              </div>
              <span className="mt-1.5 block h-2.5 overflow-hidden rounded-full bg-[#F0EFE9]">
                <span
                  className="block h-full rounded-full bg-[#3D3C38]"
                  style={{ width: `${(item.signal_count / max) * 100}%` }}
                />
              </span>
            </li>
          ))}
        </ol>
      )}
    </DashboardCard>
  )
}

export function NewPatternsCard({
  items,
  previewLimit,
  isCross,
}: {
  items: AnalyticsNewPatternItem[]
  previewLimit: number
  isCross: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? items : items.slice(0, previewLimit)
  return (
    <DashboardCard
      title="Nouveaux motifs"
      subtitle="Première apparition ici"
      titleTooltip={newPatternsVolumeTooltip()}
    >
      {items.length === 0 ? (
        <div>
          <p className="text-sm font-medium text-[#1a1a1a]">Aucun nouveau motif détecté</p>
          <p className="mt-1 text-[13px] text-[#7D7B75]">
            Aucun sujet inédit n’est apparu sur cette période.
          </p>
        </div>
      ) : (
        <>
          <ul className="flex flex-col">
            {visible.map((item) => (
              <li
                key={item.pattern_id}
                className="flex min-w-0 flex-col gap-1 border-b border-[#F0EFE9] py-3 last:border-b-0 sm:flex-row sm:items-start sm:justify-between sm:gap-3"
              >
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-[#1a1a1a]">{item.name}</span>
                  <span className="mt-0.5 block text-[12px] text-[#7D7B75]">
                    {formatRelativeDaysAgo(item.first_seen_at)}
                  </span>
                </span>
                <span className="min-w-0 text-[13px] text-[#7D7B75] sm:max-w-[48%] sm:text-right">
                  {formatNewPatternVolume({
                    isCross,
                    observationCount: item.observation_count,
                    establishmentCount: item.establishment_count,
                  })}
                </span>
              </li>
            ))}
          </ul>
          {items.length > previewLimit ? (
            <button
              type="button"
              className="mt-3 text-[12px] font-semibold text-[#1B4FD8]"
              onClick={() => setExpanded((value) => !value)}
            >
              {expanded ? 'Réduire' : 'Voir tout'}
            </button>
          ) : null}
        </>
      )}
    </DashboardCard>
  )
}

export function ContributorsCard({
  items,
  isCross,
}: {
  items: AnalyticsContributorItem[]
  isCross: boolean
}) {
  return (
    <DashboardCard title="Qui a le plus contribué">
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">
          Aucune contribution comptabilisée sur cette période
        </p>
      ) : (
        <ol className="flex flex-col">
          {items.map((item, index) => {
            const establishmentLine = isCross
              ? formatContributorEstablishments(item.establishment_names)
              : ''
            return (
              <li
                key={item.user_id}
                className="flex min-w-0 items-center justify-between gap-3 border-b border-[#F0EFE9] py-3 last:border-b-0"
              >
                <span className="flex min-w-0 items-center gap-3">
                  <span className="w-4 shrink-0 text-sm font-semibold tabular-nums text-[#1F7A4D]">
                    {index + 1}
                  </span>
                  <span
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#F0EFE9] text-[11px] font-semibold text-[#3D3C38]"
                    aria-hidden
                  >
                    {contributorInitials(item.name)}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-[#1a1a1a]">
                      {item.name}
                    </span>
                    <span className="block min-w-0 break-words text-[12px] text-[#7D7B75]">
                      {item.roles.map(formatMembershipRoleDisplay).join(', ')}
                      {' · '}
                      {formatContributorPoles(item.poles)}
                    </span>
                    {establishmentLine ? (
                      <span className="mt-0.5 block min-w-0 truncate text-[12px] text-[#7D7B75]">
                        {establishmentLine}
                      </span>
                    ) : null}
                  </span>
                </span>
                <span className="shrink-0 text-sm font-semibold tabular-nums text-[#7D7B75]">
                  {item.pts} points
                </span>
              </li>
            )
          })}
        </ol>
      )}
    </DashboardCard>
  )
}

export function ObservationTreatmentCard({
  data,
  periodDays,
}: {
  data: AnalyticsDashboardResponse
  periodDays: number
}) {
  const resolvedDuration =
    data.observation_delay_resolved.median_seconds != null
      ? formatDashboardDuration(data.observation_delay_resolved.median_seconds)
      : null
  const canceledDuration =
    data.observation_delay_canceled.median_seconds != null
      ? formatDashboardDuration(data.observation_delay_canceled.median_seconds)
      : null
  const closureHint = closureResolvedShareHint({
    measuredResolvedCount: data.closure_measured_resolved_count,
    measuredCanceledCount: data.closure_measured_canceled_count,
    undatableResolved: data.undatable_signal_terminals.resolved,
    undatableCanceled: data.undatable_signal_terminals.canceled,
  })
  const resolutionHint = operationalResolutionRateHint()

  return (
    <DashboardCard
      title="Temps de traitement"
      subtitle="Sur la période, parmi les cas déjà clôturés ou mis en plan"
    >
      <div className="flex min-w-0 flex-col gap-5 lg:grid lg:grid-cols-3 lg:gap-6">
        <DurationHero
          label="Délai pour résoudre"
          stats={data.observation_delay_resolved}
          sense="negative-up"
          emptyLabel={emptyObservationDelayMessage(
            'resolved',
            data.observation_delay_resolved.undatable_in_scope,
          )}
          hint={resolvedDuration ? medianDurationHint(resolvedDuration) : undefined}
          periodDays={periodDays}
        />
        <DurationHero
          label="Délai avant annulation"
          stats={data.observation_delay_canceled}
          sense="negative-up"
          emptyLabel={emptyObservationDelayMessage(
            'canceled',
            data.observation_delay_canceled.undatable_in_scope,
          )}
          hint={canceledDuration ? medianDurationHint(canceledDuration) : undefined}
          extraHint={observationCancellationDelayHint()}
          periodDays={periodDays}
        />
        <DurationHero
          label="Délai avant plan d’action"
          stats={data.observation_delay_transformed}
          sense="negative-up"
          emptyLabel={emptyObservationDelayMessage('transformed')}
          hint={observationTransformDelayHint()}
          periodDays={periodDays}
        />
      </div>
      <div className="mt-5 grid min-w-0 gap-4 border-t border-[#F0EFE9] pt-4 lg:grid-cols-3">
        <SecondaryMetric
          label="Part des sujets résolus"
          value={formatDashboardPercent(data.operational_resolution_rate.current_value)}
          comparison={data.operational_resolution_rate}
          sense="positive-up"
          format="points"
          hint={resolutionHint}
          tooltip={resolutionHint}
          periodDays={periodDays}
        />
        <SecondaryMetric
          label="Résolutions parmi les dossiers fermés"
          value={
            data.closure_resolved_share.current_value == null
              ? '—'
              : formatDashboardPercent(data.closure_resolved_share.current_value)
          }
          comparison={data.closure_resolved_share}
          sense="positive-up"
          format="points"
          hint={closureHint}
          tooltip={closureHint}
          periodDays={periodDays}
        />
        <SecondaryMetric
          label="Observations rouvertes"
          value={new Intl.NumberFormat('fr-FR').format(data.reopenings.current_value ?? 0)}
          comparison={data.reopenings}
          sense="negative-up"
          format="count"
          hint={reopeningsHint()}
          periodDays={periodDays}
        />
      </div>
    </DashboardCard>
  )
}

const AGING_BAR_TONES = ['bg-[#D4D1C8]', 'bg-[#B4B1A8]', 'bg-[#7D7B75]', 'bg-[#1a1a1a]']

export function OpenObservationsCard({
  data,
  periodDays,
}: {
  data: AnalyticsDashboardResponse
  periodDays: number
}) {
  const over15 = data.aging_buckets.find(isOver15dAgingBucket)
  const max = Math.max(...data.aging_buckets.map((bucket) => bucket.count), 1)

  return (
    <DashboardCard
      title="Observations encore ouvertes"
      subtitle="En ce moment · toutes les ouvertes, pas seulement la période"
    >
      {data.open_observation_count === 0 ? (
        <div>
          <p className="text-sm font-medium text-[#1a1a1a]">Aucune observation encore ouverte</p>
          <p className="mt-1 text-[13px] text-[#7D7B75]">
            Toutes les observations sont actuellement clôturées.
          </p>
        </div>
      ) : (
        <>
          <p className="text-[1.75rem] font-semibold leading-none tabular-nums tracking-tight text-[#1a1a1a] lg:text-[2rem]">
            {data.open_observation_count}
            <span className="ml-2 text-base font-medium text-[#7D7B75]">encore ouvertes</span>
          </p>
          <ul className="mt-5 flex flex-col gap-3">
            {data.aging_buckets.map((bucket, index) => (
              <li key={bucket.key} className="min-w-0">
                <div className="flex min-w-0 items-center justify-between gap-2 text-[13px]">
                  <span
                    className={cn(
                      'min-w-0 truncate text-[#7D7B75]',
                      isOver15dAgingBucket(bucket) && 'font-medium text-[#1a1a1a]',
                    )}
                  >
                    {formatAgingBucketLabel(bucket)}
                  </span>
                  <span className="shrink-0 font-semibold tabular-nums text-[#1a1a1a]">
                    {bucket.count}
                  </span>
                </div>
                <span className="mt-1.5 block h-2.5 overflow-hidden rounded-full bg-[#F0EFE9]">
                  <span
                    className={cn(
                      'block h-full rounded-full',
                      AGING_BAR_TONES[index] ?? 'bg-[#7D7B75]',
                    )}
                    style={{ width: `${(bucket.count / max) * 100}%` }}
                  />
                </span>
              </li>
            ))}
          </ul>
          {over15 ? (
            <div className="mt-4 min-w-0">
              <p className="flex min-w-0 flex-wrap items-baseline gap-2 text-sm font-medium text-[#1a1a1a]">
                {formatCountedNoun(
                  over15.count,
                  'observation ouverte depuis plus de 15 jours',
                  'observations ouvertes depuis plus de 15 jours',
                )}
                <TrendBadge
                  comparison={data.aging_over_15d_share}
                  sense="negative-up"
                  format="points"
                  periodDays={periodDays}
                />
              </p>
              <p className="mt-0.5 text-[12px] text-[#7D7B75]">
                {formatDashboardPercent(data.aging_over_15d_share.current_value)} des ouvertes
              </p>
            </div>
          ) : null}
        </>
      )}
    </DashboardCard>
  )
}

export function PlanDeadlinesCard({
  data,
  periodDays,
}: {
  data: AnalyticsDashboardResponse
  periodDays: number
}) {
  const deadlines = data.plan_deadlines
  const segments: ShareSegment[] = [
    {
      key: 'early',
      label: 'En avance',
      value: deadlines.early,
      count: deadlines.early_count,
      className: 'bg-[#1F7A4D]',
      comparison: deadlines.early_comparison,
      sense: 'positive-up',
    },
    {
      key: 'on_time',
      label: 'À temps',
      value: deadlines.on_time,
      count: deadlines.on_time_count,
      className: 'bg-[#1a1a1a]',
      comparison: deadlines.on_time_comparison,
      sense: 'neutral',
    },
    {
      key: 'late',
      label: 'En retard',
      value: deadlines.late,
      count: deadlines.late_count,
      className: 'bg-[#E24B4A]',
      comparison: deadlines.late_comparison,
      sense: 'negative-up',
      emphasize: true,
    },
  ]

  return (
    <DashboardCard title="Respect des échéances">
      {deadlines.n === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucun plan avec date d’échéance sur la période</p>
      ) : (
        <>
          <p className="text-[1.75rem] font-semibold leading-none tracking-tight text-[#1a1a1a] lg:text-[2rem]">
            {deadlines.n < 5
              ? formatLateCountOnMeasured(deadlines.late_count, deadlines.n)
              : formatDashboardPercent(deadlines.late)}
          </p>
          <p className="mt-2 min-w-0 break-words text-[13px] text-[#7D7B75]">
            {planDeadlinesDenominatorCopy()}
          </p>
          {deadlines.n >= 5 ? (
            <p className="mt-1 flex min-w-0 flex-wrap items-center gap-2 text-[13px] text-[#7D7B75]">
              {`en retard · ${formatLateCountOnMeasured(deadlines.late_count, deadlines.n)}`}
              <TrendBadge
                comparison={deadlines.late_comparison}
                sense="negative-up"
                format="points"
                periodDays={periodDays}
              />
            </p>
          ) : (
            <p className="mt-1">
              <TrendBadge
                comparison={deadlines.late_comparison}
                sense="negative-up"
                format="points"
                periodDays={periodDays}
              />
            </p>
          )}
          <div className="mt-4">
            <StackedShareBar segments={segments} periodDays={periodDays} />
          </div>
        </>
      )}
      <div className="mt-5 grid min-w-0 gap-3 border-t border-[#F0EFE9] pt-4">
        <CompactDuration
          label="Attente de validation une fois le plan terminé"
          stats={data.plan_validation}
          sense="negative-up"
          emptyLabel={emptyPlanDelayMessage('validated', {
            undatableInScope: data.plan_validation.undatable_in_scope,
          })}
          periodDays={periodDays}
        />
        <div className="grid min-w-0 gap-3 sm:grid-cols-2">
          <CompactDuration
            label="Délai d’annulation des plans"
            stats={data.plan_delay_canceled}
            sense="negative-up"
            emptyLabel={emptyPlanDelayMessage('canceled', {
              undatableInScope: data.plan_delay_canceled.undatable_in_scope,
              unstartedInScope: data.plan_delay_canceled.unstarted_in_scope,
            })}
            periodDays={periodDays}
          />
          <CompactDuration
            label="Délai de clôture des plans"
            stats={data.plan_delay_resolved}
            sense="negative-up"
            emptyLabel={emptyPlanDelayMessage('resolved', {
              undatableInScope: data.plan_delay_resolved.undatable_in_scope,
            })}
            periodDays={periodDays}
          />
        </div>
      </div>
    </DashboardCard>
  )
}

function VolumeBarList({
  items,
  previewLimit,
  showEstablishment,
  periodDays,
}: {
  items: AnalyticsNamedCountItem[]
  previewLimit?: number
  showEstablishment: boolean
  periodDays: number
}) {
  const [expanded, setExpanded] = useState(false)
  const limit = previewLimit ?? items.length
  const overflow = previewLimit != null && items.length > previewLimit
  const visible = expanded || !overflow ? items : items.slice(0, limit)
  const hiddenCount = items.length - limit
  const displayItems =
    !expanded && overflow && hiddenCount > 0
      ? [
          ...visible,
          {
            id: 'others',
            name: 'Autres',
            count: items.slice(limit).reduce((sum, item) => sum + item.count, 0),
            establishment_id: null,
            establishment_name: null,
            comparison: visible[0]?.comparison,
          } satisfies AnalyticsNamedCountItem,
        ]
      : visible
  const max = Math.max(...items.map((item) => item.count), 1)

  return (
    <>
      <ul className="flex flex-col gap-3">
        {displayItems.map((item) => (
          <li key={item.id} className="flex min-w-0 flex-col gap-1.5">
            <div className="flex min-w-0 items-end justify-between gap-2 text-sm">
              <span className="min-w-0">
                <span className="block truncate font-medium text-[#1a1a1a]">{item.name}</span>
                {showEstablishment && item.establishment_name ? (
                  <span className="mt-0.5 block truncate text-[12px] text-[#7D7B75]">
                    {item.establishment_name}
                  </span>
                ) : null}
              </span>
              <span className="flex shrink-0 flex-wrap items-center justify-end gap-2 font-semibold tabular-nums text-[#1a1a1a]">
                {formatDashboardObservationCount(item.count)}
                {item.id !== 'others' ? (
                  <TrendBadge
                    comparison={item.comparison}
                    sense="neutral"
                    format="count"
                    periodDays={periodDays}
                  />
                ) : null}
              </span>
            </div>
            <span className="h-2.5 overflow-hidden rounded-full bg-[#F0EFE9]">
              <span
                className="block h-full rounded-full bg-[#3D3C38]"
                style={{ width: `${(item.count / max) * 100}%` }}
              />
            </span>
          </li>
        ))}
      </ul>
      {overflow ? (
        <button
          type="button"
          className="mt-3 text-[12px] font-semibold text-[#1B4FD8]"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? 'Réduire' : 'Voir tout'}
        </button>
      ) : null}
    </>
  )
}

export function LocationsCard({
  items,
  previewLimit,
  isCross,
  periodDays,
}: {
  items: AnalyticsNamedCountItem[]
  previewLimit: number
  isCross: boolean
  periodDays: number
}) {
  return (
    <DashboardCard
      title="Lieux les plus cités"
      subtitle="Observations créées sur la période, pas les dossiers encore ouverts"
    >
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucun lieu cité sur la période</p>
      ) : (
        <VolumeBarList
          items={items}
          previewLimit={previewLimit}
          showEstablishment={isCross}
          periodDays={periodDays}
        />
      )}
    </DashboardCard>
  )
}

export function PolesCard({
  items,
  isCross,
  periodDays,
}: {
  items: AnalyticsNamedCountItem[]
  isCross: boolean
  periodDays: number
}) {
  return (
    <DashboardCard
      title="Activité du pôle"
      subtitle="Observations créées sur la période, selon le pôle responsable aujourd’hui"
    >
      <p className="mb-3 text-[12px] text-[#7D7B75]">{canonicalRoutingVolumeHint()}</p>
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">
          Aucune observation rattachée à un pôle sur la période
        </p>
      ) : (
        <ol className="flex flex-col">
          {items.map((item, index) => (
            <li
              key={item.id}
              className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5 border-b border-[#F0EFE9] py-3 last:border-b-0 sm:grid-cols-[auto_minmax(0,1fr)_auto_auto]"
            >
              <span className="w-4 shrink-0 text-sm font-semibold tabular-nums text-[#1F7A4D]">
                {index + 1}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium text-[#1a1a1a]">
                  {item.name}
                </span>
                {isCross && item.establishment_name ? (
                  <span className="mt-0.5 block truncate text-[12px] text-[#7D7B75]">
                    {item.establishment_name}
                  </span>
                ) : null}
              </span>
              <span className="text-right text-sm font-semibold tabular-nums text-[#1a1a1a]">
                {formatDashboardObservationCount(item.count)}
              </span>
              <span className="justify-self-end empty:hidden max-sm:col-start-3 max-sm:row-start-2">
                <TrendBadge
                  comparison={item.comparison}
                  sense="neutral"
                  format="count"
                  periodDays={periodDays}
                />
              </span>
            </li>
          ))}
        </ol>
      )}
    </DashboardCard>
  )
}
