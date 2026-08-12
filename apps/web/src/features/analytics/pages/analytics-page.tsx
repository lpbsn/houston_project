import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Repeat2,
  Target,
  TrendingUp,
} from 'lucide-react'
import type { ComponentType, SVGProps } from 'react'

import { useAuth } from '@/app/auth-provider'
import { Badge } from '@/components/ui/badge'
import {
  TerrainCard,
  TerrainEmptyState,
  TerrainErrorState,
  TerrainSectionLabel,
} from '@/components/ui/terrain'
import type { AnalyticsMetricComparison } from '@/features/analytics/api'
import { AnalyticsApiError } from '@/features/analytics/api'
import { useAnalyticsDashboardQuery } from '@/features/analytics/hooks'
import { useAnalyticsUrlState } from '@/features/analytics/lib/analytics-url-state'
import { canShowAnalyticsNavigation } from '@/features/navigation/lib/shared-navigation'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type AnalyticsIcon = ComponentType<SVGProps<SVGSVGElement>>

type KpiCardConfig = {
  title: string
  description: string
  comparison: AnalyticsMetricComparison
  icon: AnalyticsIcon
  valueFormatter?: (value: number | null) => string
}

function formatNumber(value: number | null): string {
  if (value == null) {
    return '—'
  }

  return new Intl.NumberFormat('fr-FR').format(value)
}

function formatPercentRatio(value: number | null): string {
  if (value == null) {
    return '—'
  }

  return new Intl.NumberFormat('fr-FR', {
    maximumFractionDigits: 1,
    style: 'percent',
  }).format(value)
}

function formatDurationSeconds(value: number | null): string {
  if (value == null) {
    return '—'
  }

  if (value < 60) {
    return `${Math.round(value)}s`
  }

  if (value < 3600) {
    return `${Math.round(value / 60)} min`
  }

  return `${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 }).format(value / 3600)} h`
}

function formatAbsoluteDelta(
  value: number | null,
  formatter: (value: number | null) => string,
): string {
  if (value == null) {
    return '—'
  }

  const formatted = formatter(Math.abs(value))
  if (value > 0) {
    return `+${formatted}`
  }
  if (value < 0) {
    return `-${formatted}`
  }
  return formatted
}

function formatPeriodLabel(periodStart: string, periodEnd: string): string {
  const formatter = new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
  return `${formatter.format(new Date(periodStart))} - ${formatter.format(new Date(periodEnd))}`
}

function formatTechnicalStateLabel(state: string): string {
  const labels: Record<string, string> = {
    missing_assignment: 'Sans assignment',
    not_started: 'Non démarré',
    processing: 'En traitement',
    temporary_failed: 'Échec temporaire',
    permanently_failed: 'Échec permanent',
    succeeded: 'Réussi',
  }

  return labels[state] ?? state.replaceAll('_', ' ')
}

function AnalyticsDashboardHeader({
  periodStart,
  periodEnd,
}: {
  periodStart: string
  periodEnd: string
}) {
  return (
    <div className="flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
      <div>
        <TerrainSectionLabel>Analyse</TerrainSectionLabel>
        <h1 className="text-2xl font-semibold text-[#1a1a1a] md:text-3xl">
          Dashboard Analytics
        </h1>
        <p className={cn('mt-1 text-sm', terrain.muted)}>
          Vue cross-établissement, période {formatPeriodLabel(periodStart, periodEnd)}.
        </p>
      </div>
    </div>
  )
}

function AnalyticsKpiCard({
  title,
  description,
  comparison,
  icon: Icon,
  valueFormatter = formatNumber,
}: KpiCardConfig) {
  const relativeStatus = comparison.relative_change_status
  const showRelative = relativeStatus === 'computed' && comparison.relative_change != null

  return (
    <TerrainCard className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[#1a1a1a]">{title}</p>
          <p className={cn('mt-1 text-xs leading-5', terrain.muted)}>{description}</p>
        </div>
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#E8F7F0] text-[#114660]"
          aria-hidden
        >
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <div className="mt-4 flex items-end justify-between gap-3">
        <p className="text-3xl font-semibold text-[#1a1a1a]">
          {valueFormatter(comparison.current_value)}
        </p>
        <div className="text-right">
          <p className="text-xs font-semibold text-[#555]">
            {formatAbsoluteDelta(comparison.absolute_delta, valueFormatter)}
          </p>
          <p className={cn('text-[11px]', terrain.muted)}>
            {showRelative
              ? `${formatPercentRatio(comparison.relative_change)} vs précédent`
              : 'non comparable'}
          </p>
        </div>
      </div>
    </TerrainCard>
  )
}

function AnalyticsClassificationPanel({
  totalCount,
  withPatternCount,
  withoutPatternCount,
  coverageRate,
  technicalTotalCount,
  technicalStateBreakdown,
  technicalTerminalSuccessCount,
  technicalPendingOrErrorCount,
}: {
  totalCount: number
  withPatternCount: number
  withoutPatternCount: number
  coverageRate: number | null
  technicalTotalCount: number
  technicalStateBreakdown: Record<string, number>
  technicalTerminalSuccessCount: number
  technicalPendingOrErrorCount: number
}) {
  const technicalEntries = Object.entries(technicalStateBreakdown)

  return (
    <TerrainCard className="p-4">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold text-[#1a1a1a]">Traitement Analytics</p>
        <p className={cn('text-xs leading-5', terrain.muted)}>
          Couverture métier et état technique de classification, tels que retournés par le
          backend.
        </p>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div>
          <p className={cn('text-[11px] font-semibold uppercase tracking-[0.04em]', terrain.muted)}>
            Population
          </p>
          <p className="mt-1 text-xl font-semibold text-[#1a1a1a]">{formatNumber(totalCount)}</p>
        </div>
        <div>
          <p className={cn('text-[11px] font-semibold uppercase tracking-[0.04em]', terrain.muted)}>
            Avec motif
          </p>
          <p className="mt-1 text-xl font-semibold text-[#1a1a1a]">
            {formatNumber(withPatternCount)}
          </p>
        </div>
        <div>
          <p className={cn('text-[11px] font-semibold uppercase tracking-[0.04em]', terrain.muted)}>
            Sans motif
          </p>
          <p className="mt-1 text-xl font-semibold text-[#1a1a1a]">
            {formatNumber(withoutPatternCount)}
          </p>
        </div>
        <div>
          <p className={cn('text-[11px] font-semibold uppercase tracking-[0.04em]', terrain.muted)}>
            Couverture
          </p>
          <p className="mt-1 text-xl font-semibold text-[#1a1a1a]">
            {formatPercentRatio(coverageRate)}
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Badge variant="outline" className="border-[#E8E6DF] bg-[#F7F6F2] text-[#555]">
          Technique total {formatNumber(technicalTotalCount)}
        </Badge>
        <Badge variant="outline" className="border-[#D8EADA] bg-[#F3FAF5] text-[#24614B]">
          Succès terminaux {formatNumber(technicalTerminalSuccessCount)}
        </Badge>
        <Badge variant="outline" className="border-[#F0D9C8] bg-[#FFF7EF] text-[#8A5A00]">
          Attente ou erreur {formatNumber(technicalPendingOrErrorCount)}
        </Badge>
      </div>

      {technicalEntries.length > 0 ? (
        <div className="mt-4 grid gap-2 md:grid-cols-3">
          {technicalEntries.map(([state, count]) => (
            <div
              key={state}
              className="flex items-center justify-between rounded-xl border border-[#F0EFE9] bg-[#FBFAF7] px-3 py-2 text-sm"
            >
              <span className={terrain.muted}>{formatTechnicalStateLabel(state)}</span>
              <span className="font-semibold text-[#1a1a1a]">{formatNumber(count)}</span>
            </div>
          ))}
        </div>
      ) : null}
    </TerrainCard>
  )
}

function AnalyticsDashboardSkeleton() {
  return (
    <div
      className="grid gap-3 md:grid-cols-2 xl:grid-cols-5"
      role="status"
      aria-label="Chargement Analytics"
    >
      {Array.from({ length: 5 }).map((_, index) => (
        <TerrainCard key={index} className="p-4">
          <div className="h-4 w-28 rounded-full bg-[#E8E6DF]" />
          <div className="mt-3 h-8 w-20 rounded-full bg-[#E8E6DF]" />
          <div className="mt-3 h-3 w-full rounded-full bg-[#F0EFE9]" />
        </TerrainCard>
      ))}
    </div>
  )
}

export function AnalyticsPage() {
  const { bootstrap, isBootstrapping, isReady } = useAuth()
  const analyticsState = useAnalyticsUrlState()
  const canAccessAnalytics = canShowAnalyticsNavigation(bootstrap)
  const dashboardQuery = useAnalyticsDashboardQuery(analyticsState, {
    enabled: isReady && !isBootstrapping && canAccessAnalytics,
  })

  if (!isReady || isBootstrapping) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!canAccessAnalytics) {
    return (
      <div className="flex min-h-0 flex-1 flex-col px-3 pb-4 pt-3">
        <TerrainErrorState message="Analytics est disponible pour les propriétaires, directeurs et managers." />
      </div>
    )
  }

  const data = dashboardQuery.data
  const currentKpis = data?.current_kpis
  const isEmpty = currentKpis?.analytics_signal_population_count === 0

  const kpiCards: KpiCardConfig[] = data
    ? [
        {
          title: 'Signals analysés',
          description: 'Signals avec motif exploitable.',
          comparison: data.signals_analyzed_count,
          icon: CheckCircle2,
        },
        {
          title: 'Motifs',
          description: 'Motifs visibles dans la période.',
          comparison: data.operational_patterns_count,
          icon: Target,
        },
        {
          title: 'Motifs récurrents',
          description: 'Récurrence calculée backend.',
          comparison: data.recurring_patterns_count,
          icon: Repeat2,
        },
        {
          title: 'À traiter',
          description: 'Signals actionable Analytics.',
          comparison: data.actionable_signals_count,
          icon: AlertCircle,
        },
        {
          title: 'Médiane résolution',
          description: 'Durée médiane valide.',
          comparison: data.median_resolution_seconds,
          icon: Clock3,
          valueFormatter: formatDurationSeconds,
        },
      ]
    : []

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 px-3 pb-5 pt-3 md:px-5 lg:px-6">
      <AnalyticsDashboardHeader
        periodStart={analyticsState.periodStart}
        periodEnd={analyticsState.periodEnd}
      />

      {dashboardQuery.isLoading ? <AnalyticsDashboardSkeleton /> : null}

      {dashboardQuery.isError ? (
        <TerrainErrorState
          message={resolveApiErrorMessage(
            dashboardQuery.error,
            AnalyticsApiError,
            'Impossible de charger Analytics.',
          )}
          onRetry={() => void dashboardQuery.refetch()}
        />
      ) : null}

      {data ? (
        <>
          {isEmpty ? (
            <TerrainEmptyState
              title="Aucune donnée Analytics visible"
              description="Les indicateurs restent disponibles dès que des Signals entrent dans le scope Analytics."
            />
          ) : null}

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {kpiCards.map((card) => (
              <AnalyticsKpiCard key={card.title} {...card} />
            ))}
          </div>

          <AnalyticsClassificationPanel
            totalCount={currentKpis.business_assignment_coverage.total_count}
            withPatternCount={currentKpis.business_assignment_coverage.with_pattern_count}
            withoutPatternCount={currentKpis.business_assignment_coverage.without_pattern_count}
            coverageRate={currentKpis.business_assignment_coverage.coverage_rate}
            technicalTotalCount={currentKpis.technical_classification_state.total_count}
            technicalStateBreakdown={
              currentKpis.technical_classification_state.technical_state_breakdown
            }
            technicalTerminalSuccessCount={
              currentKpis.technical_classification_state.technical_terminal_success_count
            }
            technicalPendingOrErrorCount={
              currentKpis.technical_classification_state.technical_pending_or_error_count
            }
          />

          <TerrainCard className="p-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-[#114660]" aria-hidden />
              <p className="text-sm font-semibold text-[#1a1a1a]">Contexte de comparaison</p>
            </div>
            <p className={cn('mt-2 text-xs leading-5', terrain.muted)}>
              Période précédente :{' '}
              {formatPeriodLabel(
                data.previous_period.period_start,
                data.previous_period.period_end,
              )}
              . Les variations affichées utilisent les valeurs de comparaison retournées par
              l’API.
            </p>
          </TerrainCard>
        </>
      ) : null}
    </div>
  )
}
