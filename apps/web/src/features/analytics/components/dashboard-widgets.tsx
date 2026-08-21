import { useState, type ReactNode } from 'react'
import { ArrowDownRight, ArrowUpRight, Clock, Download } from 'lucide-react'

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
  DASHBOARD_INSUFFICIENT_P90_COPY,
  DASHBOARD_VS_PREVIOUS_PERIOD,
  dashboardNewLabel,
  dashboardTrendTone,
  emptyObservationDelayMessage,
  emptyPlanDelayMessage,
  formatDashboardCountDelta,
  formatDashboardDuration,
  formatDashboardPercent,
  formatDashboardPercentDelta,
  formatDashboardPointsDelta,
  formatMeasuredSample,
  formatRelativeDaysAgo,
  medianDurationHint,
  type DashboardTrendSense,
} from '@/features/analytics/lib/dashboard-comparisons'
import { formatMembershipRoleDisplay } from '@/lib/display-names'
import { cn } from '@/lib/utils'

function DashboardCard({
  title,
  children,
  footer,
  className,
}: {
  title: string
  children: ReactNode
  footer?: string
  className?: string
}) {
  return (
    <section
      className={cn(
        'flex h-full min-w-0 max-w-full flex-col rounded-2xl border border-[#E8E6DF] bg-white p-5',
        className,
      )}
    >
      <h2 className="text-base font-semibold tracking-tight text-[#1a1a1a]">{title}</h2>
      <div className="mt-4 flex-1">{children}</div>
      {footer ? (
        <p className="mt-4 text-[10px] font-medium uppercase tracking-[0.16em] text-[#A8A59E]">
          {footer}
        </p>
      ) : null}
    </section>
  )
}

function TrendBadge({
  comparison,
  sense,
  format = 'percent',
}: {
  comparison: AnalyticsDashboardMetricComparison
  sense: DashboardTrendSense
  format?: 'percent' | 'points' | 'count' | 'duration'
}) {
  if (!canShowDashboardDelta(comparison)) {
    return null
  }
  if (dashboardNewLabel(comparison)) {
    return <span className="text-[11px] font-semibold text-[#1F7A4D]">Nouveau</span>
  }
  const delta =
    format === 'points' || format === 'count'
      ? comparison.absolute_delta
      : comparison.relative_change
  const label =
    format === 'points'
      ? formatDashboardPointsDelta(comparison.relative_change)
      : format === 'count'
        ? formatDashboardCountDelta(comparison.absolute_delta)
        : formatDashboardPercentDelta(comparison.relative_change)
  if (!label) {
    return null
  }
  const tone = dashboardTrendTone(delta, sense)
  const Icon = (delta ?? 0) < 0 ? ArrowDownRight : ArrowUpRight
  return (
    <span
      className={cn(
        'inline-flex min-w-0 flex-wrap items-center gap-0.5 text-[11px] font-semibold',
        tone === 'positive' && 'text-[#1F7A4D]',
        tone === 'negative' && 'text-[#E24B4A]',
        tone === 'neutral' && 'text-[#7D7B75]',
      )}
    >
      <Icon className="h-3 w-3" aria-hidden />
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

function StackedShareBar({ segments }: { segments: ShareSegment[] }) {
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
              'flex min-w-0 flex-wrap items-center gap-1.5 text-[12px] text-[#7D7B75]',
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
              <TrendBadge comparison={segment.comparison} sense={segment.sense} format="points" />
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

function DurationKpi({
  label,
  stats,
  sense,
  showP90,
  emptyLabel,
  unit = 'observation',
  size = 'hero',
}: {
  label: string
  stats: AnalyticsDelayStats
  sense: DashboardTrendSense
  showP90: boolean
  emptyLabel: string
  unit?: 'observation' | 'plan'
  size?: 'hero' | 'compact'
}) {
  if (stats.n === 0 || stats.median_seconds == null) {
    return (
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#7D7B75]">
          {label}
        </p>
        <p className="mt-2 text-sm text-[#7D7B75]">{emptyLabel}</p>
      </div>
    )
  }

  const duration = formatDashboardDuration(stats.median_seconds)
  const mean = formatDashboardDuration(stats.mean_seconds)
  const p90Ready = showP90 && stats.n >= 10 && stats.p90_seconds != null
  const hintParts = [
    medianDurationHint(duration),
    `Moyenne ${mean}`,
    p90Ready
      ? `P90 ${formatDashboardDuration(stats.p90_seconds)}`
      : showP90
        ? DASHBOARD_INSUFFICIENT_P90_COPY
        : null,
    formatMeasuredSample(stats.n, unit),
  ].filter(Boolean)

  return (
    <div title={hintParts.join(' · ')}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#7D7B75]">
        {label}
      </p>
      <p
        className={cn(
          'mt-1 flex min-w-0 flex-wrap items-baseline gap-2 font-semibold tabular-nums text-[#1a1a1a]',
          size === 'hero' ? 'text-2xl' : 'text-lg',
        )}
      >
        {duration}
        <TrendBadge comparison={stats.comparison} sense={sense} format="duration" />
      </p>
      <p className="mt-1 min-w-0 break-words text-[12px] text-[#7D7B75]">
        Médiane · moy. {mean}
        {p90Ready ? ` · P90 ${formatDashboardDuration(stats.p90_seconds)}` : ''}
        {` · ${formatMeasuredSample(stats.n, unit)}`}
      </p>
      {showP90 && !p90Ready ? (
        <p className="mt-0.5 text-[11px] text-[#A8A59E]">{DASHBOARD_INSUFFICIENT_P90_COPY}</p>
      ) : null}
    </div>
  )
}

function SecondaryMetric({
  label,
  value,
  comparison,
  sense,
  format,
}: {
  label: string
  value: string
  comparison: AnalyticsDashboardMetricComparison
  sense: DashboardTrendSense
  format: 'percent' | 'points' | 'count' | 'duration'
}) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#7D7B75]">{label}</p>
      <p className="mt-1 flex min-w-0 flex-wrap items-baseline gap-2 text-lg font-semibold tabular-nums text-[#1a1a1a]">
        {value}
        <TrendBadge comparison={comparison} sense={sense} format={format} />
      </p>
    </div>
  )
}

export function DashboardAiSummaryPlaceholder() {
  return (
    <section className="min-w-0 max-w-full rounded-2xl border border-[#E8E6DF] bg-white px-5 py-4">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        <p className="min-w-0 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#1F7A4D]">
          Résumé de la semaine · généré par IA
        </p>
        <span className="inline-flex rounded-full border border-[#E8E6DF] px-2.5 py-1 text-[11px] font-semibold text-[#7D7B75]">
          Bientôt disponible
        </span>
      </div>
    </section>
  )
}

export function DashboardRevenuePlaceholder() {
  return (
    <section className="flex h-full min-w-0 max-w-full flex-col rounded-2xl border border-[#E8E6DF] bg-white p-5">
      <h2 className="text-base font-semibold tracking-tight text-[#1a1a1a]">
        CA vs Observations
      </h2>
      <div className="mt-4 flex min-h-[12rem] flex-1 flex-col items-center justify-center rounded-xl border border-dashed border-[#D6D3CB] px-6 py-8">
        <span className="rounded-full bg-[#1a1a1a] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-white">
          Bientôt disponible
        </span>
        <p className="mt-3 max-w-sm text-center text-sm text-[#7D7B75]">
          Nécessite l’intégration de votre caisse. Aucun chiffre n’est affiché tant que la donnée
          réelle n’est pas connectée.
        </p>
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
      title="Bientôt disponible"
    >
      <Download className="h-4 w-4" aria-hidden />
      Exporter
    </button>
  )
}

export function RecurringPatternsCard({
  items,
}: {
  items: AnalyticsRecurringPatternItem[]
}) {
  return (
    <DashboardCard title="Motifs récurrents" footer={DASHBOARD_VS_PREVIOUS_PERIOD}>
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucun motif récurrent sur la période.</p>
      ) : (
        <ul className="flex flex-col">
          {items.map((item) => (
            <li
              key={item.pattern_id}
              className="flex min-w-0 items-center justify-between gap-3 border-b border-[#F0EFE9] py-3 last:border-b-0"
            >
              <span className="min-w-0 truncate text-sm font-medium text-[#1a1a1a]">
                {item.name}
              </span>
              <span className="flex shrink-0 items-center gap-2 text-sm font-semibold tabular-nums text-[#1a1a1a]">
                {item.signal_count}
                <TrendBadge comparison={item.comparison} sense="negative-up" />
              </span>
            </li>
          ))}
        </ul>
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
    <DashboardCard title="Nouveaux motifs">
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucun nouveau motif sur la période.</p>
      ) : (
        <>
          <ul className="flex flex-col">
            {visible.map((item) => (
              <li
                key={item.pattern_id}
                className="flex items-start justify-between gap-3 border-b border-[#F0EFE9] py-3 last:border-b-0"
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium text-[#1a1a1a]">
                    {item.name}
                  </span>
                  <span className="mt-0.5 block text-[12px] text-[#7D7B75]">
                    {formatRelativeDaysAgo(item.first_seen_at)}
                  </span>
                </span>
                <span className="min-w-0 max-w-[58%] break-words rounded-full border border-[#E8E6DF] px-2.5 py-0.5 text-right text-[11px] text-[#7D7B75]">
                  {isCross
                    ? `${item.observation_count} observations · ${item.establishment_count ?? 0} établissements`
                    : `${item.observation_count} observations depuis sa détection`}
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

export function ContributorsCard({ items }: { items: AnalyticsContributorItem[] }) {
  return (
    <DashboardCard title="Classement des contributeurs">
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucun point enregistré sur la période.</p>
      ) : (
        <ol className="flex flex-col">
          {items.map((item, index) => (
            <li
              key={item.user_id}
              className="flex items-center justify-between gap-3 border-b border-[#F0EFE9] py-3 last:border-b-0"
            >
              <span className="flex min-w-0 items-center gap-3">
                <span className="w-4 shrink-0 text-sm font-semibold tabular-nums text-[#1F7A4D]">
                  {index + 1}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium text-[#1a1a1a]">
                    {item.name}
                  </span>
                  <span className="block truncate text-[12px] text-[#7D7B75]">
                    {item.roles.map(formatMembershipRoleDisplay).join(', ')}
                    {' · '}
                    {item.poles.join(', ') || 'Sans pôle'}
                  </span>
                </span>
              </span>
              <span className="shrink-0 text-base font-semibold tabular-nums text-[#1a1a1a]">
                {item.pts} pts
              </span>
            </li>
          ))}
        </ol>
      )}
    </DashboardCard>
  )
}

export function ObservationTreatmentCard({ data }: { data: AnalyticsDashboardResponse }) {
  return (
    <DashboardCard title="Temps de traitement">
      <div className="grid min-w-0 gap-3 lg:grid-cols-3">
        <div className="min-w-0 rounded-xl bg-[#F7F6F2] px-3 py-3">
          <DurationKpi
            label="Temps avant annulation"
            stats={data.observation_delay_canceled}
            sense="negative-up"
            showP90
            emptyLabel={emptyObservationDelayMessage('canceled')}
          />
        </div>
        <div className="min-w-0 rounded-xl bg-[#F7F6F2] px-3 py-3">
          <DurationKpi
            label="Temps avant résolution"
            stats={data.observation_delay_resolved}
            sense="negative-up"
            showP90
            emptyLabel={emptyObservationDelayMessage('resolved')}
          />
        </div>
        <div className="min-w-0 rounded-xl bg-[#F7F6F2] px-3 py-3">
          <DurationKpi
            label="Temps avant mise en plan"
            stats={data.observation_delay_transformed}
            sense="negative-up"
            showP90
            emptyLabel={emptyObservationDelayMessage('transformed')}
          />
        </div>
      </div>
      <div className="mt-4 grid min-w-0 gap-3 rounded-xl border border-[#E8E6DF] px-3 py-3 lg:grid-cols-3">
        <SecondaryMetric
          label="Part de la charge résolue"
          value={formatDashboardPercent(data.operational_resolution_rate.current_value)}
          comparison={data.operational_resolution_rate}
          sense="positive-up"
          format="points"
        />
        <SecondaryMetric
          label="Part résolue parmi les clôtures"
          value={formatDashboardPercent(data.closure_resolved_share.current_value)}
          comparison={data.closure_resolved_share}
          sense="positive-up"
          format="points"
        />
        <SecondaryMetric
          label="Observations rouvertes"
          value={new Intl.NumberFormat('fr-FR').format(data.reopenings.current_value ?? 0)}
          comparison={data.reopenings}
          sense="negative-up"
          format="count"
        />
      </div>
    </DashboardCard>
  )
}

function isOver15dBucket(bucket: { key: string; label: string }): boolean {
  return bucket.key === '> 15 j' || bucket.key === 'gt_15d' || bucket.label.includes('> 15')
}

const AGING_BAR_TONES = ['bg-[#D4D1C8]', 'bg-[#B4B1A8]', 'bg-[#7D7B75]', 'bg-[#1a1a1a]']

export function OpenObservationsCard({ data }: { data: AnalyticsDashboardResponse }) {
  const over15 = data.aging_buckets.find(isOver15dBucket)
  const segments: ShareSegment[] = data.aging_buckets.map((bucket, index) => ({
    key: bucket.key,
    label: bucket.label,
    value: bucket.share,
    count: bucket.count,
    className: AGING_BAR_TONES[index] ?? 'bg-[#7D7B75]',
    emphasize: isOver15dBucket(bucket),
  }))

  return (
    <DashboardCard title="Observations encore ouvertes">
      {data.open_observation_count === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucune observation ouverte.</p>
      ) : (
        <>
          <p className="text-3xl font-semibold tabular-nums tracking-tight text-[#1a1a1a]">
            {data.open_observation_count}
            <span className="ml-2 text-base font-medium text-[#7D7B75]">ouvertes</span>
          </p>
          <div className="mt-4">
            <StackedShareBar segments={segments} />
          </div>
          {over15 ? (
            <div className="mt-4 rounded-xl bg-[#F7F6F2] px-3 py-3">
              <SecondaryMetric
                label="Toujours ouvertes depuis plus de 15 j"
                value={`${over15.count} · ${formatDashboardPercent(data.aging_over_15d_share.current_value)}`}
                comparison={data.aging_over_15d_share}
                sense="negative-up"
                format="points"
              />
            </div>
          ) : null}
        </>
      )}
    </DashboardCard>
  )
}

export function PlanDeadlinesCard({ data }: { data: AnalyticsDashboardResponse }) {
  const deadlines = data.plan_deadlines
  const segments: ShareSegment[] = [
    {
      key: 'early',
      label: 'En avance',
      value: deadlines.early,
      className: 'bg-[#1F7A4D]',
      comparison: deadlines.early_comparison,
      sense: 'positive-up',
    },
    {
      key: 'on_time',
      label: 'À temps',
      value: deadlines.on_time,
      className: 'bg-[#1a1a1a]',
      comparison: deadlines.on_time_comparison,
      sense: 'neutral',
    },
    {
      key: 'late',
      label: 'En retard',
      value: deadlines.late,
      className: 'bg-[#E24B4A]',
      comparison: deadlines.late_comparison,
      sense: 'negative-up',
      emphasize: true,
    },
  ]

  return (
    <DashboardCard title="Respect des échéances">
      {deadlines.n === 0 ? (
        <p className="text-sm text-[#7D7B75]">
          Aucun plan avec échéance mesurable sur la période.
        </p>
      ) : (
        <StackedShareBar segments={segments} />
      )}
      <div className="mt-5 flex items-start gap-2.5 border-t border-[#E8E6DF] pt-4">
        <Clock className="mt-1 h-4 w-4 shrink-0 text-[#7D7B75]" aria-hidden />
        <DurationKpi
          label="Temps avant validation"
          stats={data.plan_validation}
          sense="negative-up"
          showP90={false}
          emptyLabel={emptyPlanDelayMessage('validated')}
          unit="plan"
          size="compact"
        />
      </div>
      <div className="mt-4 grid min-w-0 gap-3 lg:grid-cols-2">
        <DurationKpi
          label="Plans — annulation"
          stats={data.plan_delay_canceled}
          sense="negative-up"
          showP90={false}
          emptyLabel={emptyPlanDelayMessage('canceled')}
          unit="plan"
          size="compact"
        />
        <DurationKpi
          label="Plans — résolution"
          stats={data.plan_delay_resolved}
          sense="negative-up"
          showP90={false}
          emptyLabel={emptyPlanDelayMessage('resolved')}
          unit="plan"
          size="compact"
        />
      </div>
    </DashboardCard>
  )
}

function VolumeBarList({
  items,
  previewLimit,
  showEstablishment,
}: {
  items: AnalyticsNamedCountItem[]
  previewLimit?: number
  showEstablishment: boolean
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
          <li key={item.id} className="flex flex-col gap-1.5">
            <div className="flex min-w-0 items-center justify-between gap-2 text-sm">
              <span className="min-w-0 truncate font-medium text-[#1a1a1a]">
                {item.name}
                {showEstablishment && item.establishment_name ? (
                  <span className="ml-2 rounded-full bg-[#F0EFE9] px-1.5 py-0.5 text-[10px] font-semibold text-[#7D7B75]">
                    {item.establishment_name}
                  </span>
                ) : null}
              </span>
              <span className="flex shrink-0 flex-wrap items-center gap-2 font-semibold tabular-nums text-[#1a1a1a]">
                {item.count}
                {item.id !== 'others' ? (
                  <TrendBadge comparison={item.comparison} sense="neutral" />
                ) : null}
              </span>
            </div>
            <span className="h-3 overflow-hidden rounded-full bg-[#F0EFE9]">
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

export function ZonesCard({
  items,
  previewLimit,
  isCross,
}: {
  items: AnalyticsNamedCountItem[]
  previewLimit: number
  isCross: boolean
}) {
  return (
    <DashboardCard title="Zones les plus signalées">
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucune zone signalée sur la période.</p>
      ) : (
        <VolumeBarList items={items} previewLimit={previewLimit} showEstablishment={isCross} />
      )}
    </DashboardCard>
  )
}

export function PolesCard({
  items,
  isCross,
}: {
  items: AnalyticsNamedCountItem[]
  isCross: boolean
}) {
  return (
    <DashboardCard title="Activité du pôle" footer={DASHBOARD_VS_PREVIOUS_PERIOD}>
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucune activité de pôle sur la période.</p>
      ) : (
        <ul className="flex flex-col">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex min-w-0 items-center justify-between gap-3 border-b border-[#F0EFE9] py-3 last:border-b-0"
            >
              <span className="min-w-0 truncate text-sm font-medium text-[#1a1a1a]">
                {item.name}
                {isCross && item.establishment_name ? (
                  <span className="ml-2 rounded-full bg-[#F0EFE9] px-1.5 py-0.5 text-[10px] font-semibold text-[#7D7B75]">
                    {item.establishment_name}
                  </span>
                ) : null}
              </span>
              <span className="flex shrink-0 items-center gap-2 text-sm font-semibold tabular-nums text-[#1a1a1a]">
                {item.count}
                <TrendBadge comparison={item.comparison} sense="neutral" />
              </span>
            </li>
          ))}
        </ul>
      )}
    </DashboardCard>
  )
}
