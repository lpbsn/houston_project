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
  dashboardNewLabel,
  dashboardTrendTone,
  formatDashboardCountDelta,
  formatDashboardDuration,
  formatDashboardPercent,
  formatDashboardPercentDelta,
  formatDashboardPointsDelta,
  formatRelativeDaysAgo,
  type DashboardTrendSense,
} from '@/features/analytics/lib/dashboard-comparisons'
import { formatMembershipRoleDisplay } from '@/lib/display-names'
import { cn } from '@/lib/utils'

function DashboardCard({
  title,
  children,
  className,
}: {
  title: string
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cn('rounded-2xl border border-[#E8E6DF] bg-white p-5', className)}>
      <h2 className="text-sm font-semibold text-[#1a1a1a]">{title}</h2>
      <div className="mt-4">{children}</div>
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
    if (comparison.coverage === 'partial' || comparison.coverage === 'not_comparable') {
      return <span className="text-[11px] font-medium text-[#7D7B75]">Données incomplètes</span>
    }
    return null
  }
  if (dashboardNewLabel(comparison)) {
    return (
      <span className="text-[11px] font-semibold text-[#1F7A4D]">Nouveau</span>
    )
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
        'inline-flex items-center gap-0.5 text-[11px] font-semibold',
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

export function DashboardComingSoonCard({ title, message }: { title: string; message: string }) {
  return (
    <DashboardCard title={title}>
      <p className="text-sm text-[#7D7B75]">{message}</p>
      <span className="mt-3 inline-flex rounded-full border border-[#1F7A4D]/30 px-2.5 py-1 text-[11px] font-semibold text-[#1F7A4D]">
        Bientôt disponible
      </span>
    </DashboardCard>
  )
}

export function DashboardExportButton() {
  return (
    <button
      type="button"
      disabled
      className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#1F7A4D] px-3 text-sm font-semibold text-white opacity-70"
      title="Bientôt disponible"
    >
      <Download className="h-4 w-4" aria-hidden />
      Exporter
      <span className="text-[10px] font-medium text-white/80">Bientôt disponible</span>
    </button>
  )
}

export function RecurringPatternsCard({
  items,
}: {
  items: AnalyticsRecurringPatternItem[]
}) {
  return (
    <DashboardCard title="Motifs récurrents">
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucun motif récurrent sur la période.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {items.map((item) => (
            <li key={item.pattern_id} className="flex items-start justify-between gap-3">
              <span className="min-w-0 text-sm font-medium text-[#1a1a1a]">{item.name}</span>
              <span className="flex shrink-0 items-center gap-2 text-sm tabular-nums">
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
          <ul className="flex flex-col gap-3">
            {visible.map((item) => (
              <li key={item.pattern_id} className="flex flex-col gap-0.5">
                <span className="text-sm font-medium text-[#1a1a1a]">{item.name}</span>
                <span className="text-[12px] text-[#7D7B75]">
                  {formatRelativeDaysAgo(item.first_seen_at)}
                  {' · '}
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
        <ol className="flex flex-col gap-3">
          {items.map((item, index) => (
            <li key={item.user_id} className="flex items-start justify-between gap-3">
              <span className="flex min-w-0 items-start gap-2">
                <span
                  className={cn(
                    'mt-0.5 flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold',
                    index < 3 ? 'bg-[#1F7A4D] text-white' : 'bg-[#F0EFE9] text-[#7D7B75]',
                  )}
                >
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
              <span className="shrink-0 text-sm font-semibold tabular-nums text-[#1a1a1a]">
                {item.pts} pts
              </span>
            </li>
          ))}
        </ol>
      )}
    </DashboardCard>
  )
}

function DelayBlock({
  label,
  stats,
  sense,
  showP90,
}: {
  label: string
  stats: AnalyticsDelayStats
  sense: DashboardTrendSense
  showP90: boolean
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[12px] font-semibold uppercase tracking-wide text-[#7D7B75]">{label}</p>
        <TrendBadge comparison={stats.comparison} sense={sense} format="duration" />
      </div>
      <p className="text-lg font-semibold tabular-nums text-[#1a1a1a]">
        {formatDashboardDuration(stats.median_seconds)}
      </p>
      <p className="text-[12px] text-[#7D7B75]">
        Médiane · moyenne {formatDashboardDuration(stats.mean_seconds)}
        {showP90
          ? stats.n >= 10
            ? ` · P90 ${formatDashboardDuration(stats.p90_seconds)}`
            : ' · P90 données insuffisantes'
          : ''}
        {` · n ${stats.n}`}
      </p>
    </div>
  )
}

export function ObservationPerformanceCard({ data }: { data: AnalyticsDashboardResponse }) {
  return (
    <DashboardCard title="Observations — délais et résolution">
      <div className="grid gap-4 sm:grid-cols-3">
        <DelayBlock
          label="Annulation"
          stats={data.observation_delay_canceled}
          sense="negative-up"
          showP90
        />
        <DelayBlock
          label="Résolution"
          stats={data.observation_delay_resolved}
          sense="negative-up"
          showP90
        />
        <DelayBlock
          label="Transformation en plan"
          stats={data.observation_delay_transformed}
          sense="negative-up"
          showP90
        />
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <MetricLine
          label="Taux de résolution opérationnel"
          value={formatDashboardPercent(data.operational_resolution_rate.current_value)}
          comparison={data.operational_resolution_rate}
          sense="positive-up"
          format="points"
        />
        <MetricLine
          label="Part des clôtures résolues"
          value={formatDashboardPercent(data.closure_resolved_share.current_value)}
          comparison={data.closure_resolved_share}
          sense="positive-up"
          format="points"
        />
        <MetricLine
          label="Réouvertures"
          value={new Intl.NumberFormat('fr-FR').format(data.reopenings.current_value ?? 0)}
          comparison={data.reopenings}
          sense="negative-up"
          format="count"
        />
      </div>
    </DashboardCard>
  )
}

function MetricLine({
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
      <p className="text-[12px] text-[#7D7B75]">{label}</p>
      <p className="mt-1 flex items-center gap-2 text-base font-semibold text-[#1a1a1a]">
        {value}
        <TrendBadge comparison={comparison} sense={sense} format={format} />
      </p>
    </div>
  )
}

export function ObservationAgingCard({ data }: { data: AnalyticsDashboardResponse }) {
  return (
    <DashboardCard title="Ancienneté des observations ouvertes">
      <p className="text-2xl font-semibold tabular-nums text-[#1a1a1a]">
        {data.open_observation_count}
        <span className="ml-2 text-sm font-medium text-[#7D7B75]">ouvertes</span>
      </p>
      <ul className="mt-4 flex flex-col gap-2">
        {data.aging_buckets.map((bucket) => (
          <li key={bucket.key} className="flex items-center justify-between text-sm">
            <span className="text-[#7D7B75]">{bucket.label}</span>
            <span className="tabular-nums text-[#1a1a1a]">
              {bucket.count}
              {bucket.share != null ? ` · ${formatDashboardPercent(bucket.share)}` : ''}
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-4">
        <MetricLine
          label="Part > 15 j"
          value={formatDashboardPercent(data.aging_over_15d_share.current_value)}
          comparison={data.aging_over_15d_share}
          sense="negative-up"
          format="points"
        />
      </div>
    </DashboardCard>
  )
}

export function PlanPerformanceCard({ data }: { data: AnalyticsDashboardResponse }) {
  const deadlines = data.plan_deadlines
  const segments = [
    { key: 'early', label: 'En avance', value: deadlines.early, className: 'bg-[#1F7A4D]' },
    { key: 'on_time', label: 'À temps', value: deadlines.on_time, className: 'bg-[#1a1a1a]' },
    { key: 'late', label: 'En retard', value: deadlines.late, className: 'bg-[#E24B4A]' },
  ]
  return (
    <DashboardCard title="Plans d’action — délais et échéances">
      <div className="grid gap-4 sm:grid-cols-3">
        <DelayBlock
          label="Annulation"
          stats={data.plan_delay_canceled}
          sense="negative-up"
          showP90={false}
        />
        <DelayBlock
          label="Résolution"
          stats={data.plan_delay_resolved}
          sense="negative-up"
          showP90={false}
        />
        <DelayBlock
          label="Temps de validation"
          stats={data.plan_validation}
          sense="negative-up"
          showP90={false}
        />
      </div>
      <div className="mt-5">
        <p className="text-[12px] font-semibold uppercase tracking-wide text-[#7D7B75]">
          Respect des échéances
        </p>
        <div className="mt-2 flex h-2.5 overflow-hidden rounded-full bg-[#F0EFE9]">
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
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-[12px]">
          <li className="flex items-center gap-2">
            En avance {formatDashboardPercent(deadlines.early)}
            <TrendBadge comparison={deadlines.early_comparison} sense="positive-up" format="points" />
          </li>
          <li className="flex items-center gap-2">
            À temps {formatDashboardPercent(deadlines.on_time)}
            <TrendBadge comparison={deadlines.on_time_comparison} sense="neutral" format="points" />
          </li>
          <li className="flex items-center gap-2">
            En retard {formatDashboardPercent(deadlines.late)}
            <TrendBadge comparison={deadlines.late_comparison} sense="negative-up" format="points" />
          </li>
        </ul>
      </div>
    </DashboardCard>
  )
}

function NamedCountList({
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
          } satisfies AnalyticsNamedCountItem & { comparison: AnalyticsNamedCountItem['comparison'] },
        ]
      : visible
  const max = Math.max(...items.map((item) => item.count), 1)

  return (
    <>
      <ul className="flex flex-col gap-2">
        {displayItems.map((item) => (
          <li key={item.id} className="flex flex-col gap-1">
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className="min-w-0 truncate font-medium text-[#1a1a1a]">
                {item.name}
                {showEstablishment && item.establishment_name ? (
                  <span className="ml-2 rounded-full bg-[#F0EFE9] px-1.5 py-0.5 text-[10px] font-semibold text-[#7D7B75]">
                    {item.establishment_name}
                  </span>
                ) : null}
              </span>
              <span className="flex items-center gap-2 tabular-nums">
                {item.count}
                {item.id !== 'others' ? (
                  <TrendBadge comparison={item.comparison} sense="neutral" />
                ) : null}
              </span>
            </div>
            <span className="h-1.5 overflow-hidden rounded-full bg-[#F0EFE9]">
              <span
                className="block h-full rounded-full bg-[#1a1a1a]/70"
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
        <NamedCountList items={items} previewLimit={previewLimit} showEstablishment={isCross} />
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
    <DashboardCard title="Activité du pôle">
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucune activité de pôle sur la période.</p>
      ) : (
        <NamedCountList items={items} showEstablishment={isCross} />
      )}
    </DashboardCard>
  )
}
