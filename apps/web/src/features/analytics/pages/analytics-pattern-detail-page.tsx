import {
  Activity,
  AlertCircle,
  ArrowLeft,
  Building2,
  Clock3,
  Repeat2,
  TrendingUp,
} from 'lucide-react'
import type { ComponentType, SVGProps } from 'react'

import { useAuth } from '@/app/auth-provider'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  TerrainCard,
  TerrainEmptyState,
  TerrainErrorState,
  TerrainSectionLabel,
} from '@/components/ui/terrain'
import type {
  AnalyticsMetricComparison,
  AnalyticsPatternDetailResponse,
} from '@/features/analytics/api'
import { AnalyticsApiError } from '@/features/analytics/api'
import { useAnalyticsPatternDetailQuery } from '@/features/analytics/hooks'
import {
  buildAnalyticsReturnPath,
  type AnalyticsUrlState,
} from '@/features/analytics/lib/analytics-url-state'
import { canShowAnalyticsNavigation } from '@/features/navigation/lib/shared-navigation'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type AnalyticsIcon = ComponentType<SVGProps<SVGSVGElement>>

type AnalyticsPatternDetailPageProps = {
  patternId: string
  analyticsState: AnalyticsUrlState
  onNavigate: (pathname: string, options?: { replace?: boolean }) => void
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

function formatAbsoluteDelta(value: number | null): string {
  if (value == null) {
    return '—'
  }

  const formatted = formatNumber(Math.abs(value))
  if (value > 0) {
    return `+${formatted}`
  }
  if (value < 0) {
    return `-${formatted}`
  }
  return formatted
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return '—'
  }

  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
  }).format(new Date(value))
}

const BACKEND_BUCKET_MONTH_LABELS = [
  'janv.',
  'févr.',
  'mars',
  'avr.',
  'mai',
  'juin',
  'juil.',
  'août',
  'sept.',
  'oct.',
  'nov.',
  'déc.',
]

function formatBackendBucketDate(bucketDate: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(bucketDate)
  if (!match) {
    return bucketDate
  }

  const monthIndex = Number(match[2]) - 1
  const day = Number(match[3])
  const monthLabel = BACKEND_BUCKET_MONTH_LABELS[monthIndex]
  if (!monthLabel || day < 1 || day > 31) {
    return bucketDate
  }

  return `${String(day).padStart(2, '0')} ${monthLabel}`
}

function formatPeriod(start: string, end: string): string {
  return `${formatDate(start)} - ${formatDate(end)}`
}

function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    archived: 'Archivé',
    in_progress: 'En cours',
    interesting: 'Intéressant',
    open: 'Ouvert',
    resolved: 'Résolu',
  }

  return labels[status] ?? status.replaceAll('_', ' ')
}

function ComparisonSummary({ comparison }: { comparison: AnalyticsMetricComparison }) {
  const showRelative =
    comparison.relative_change_status === 'computed' && comparison.relative_change != null

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <Badge variant="outline" className="border-[#E8E6DF] bg-[#F7F6F2] text-[#555]">
        Précédent {formatNumber(comparison.previous_value)}
      </Badge>
      <Badge variant="outline" className="border-[#D8EADA] bg-[#F3FAF5] text-[#24614B]">
        Écart {formatAbsoluteDelta(comparison.absolute_delta)}
      </Badge>
      <span className={terrain.muted}>
        {showRelative ? `${formatPercentRatio(comparison.relative_change)} vs précédent` : 'non comparable'}
      </span>
    </div>
  )
}

function MetricCard({
  title,
  value,
  icon: Icon,
  description,
}: {
  title: string
  value: string
  icon: AnalyticsIcon
  description: string
}) {
  return (
    <TerrainCard className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
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
      <p className="mt-4 text-2xl font-semibold text-[#1a1a1a]">{value}</p>
    </TerrainCard>
  )
}

function InlineMetric({
  title,
  value,
  description,
}: {
  title: string
  value: string
  description: string
}) {
  return (
    <div className="rounded-xl border border-[#F0EFE9] bg-[#FBFAF7] p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.04em] text-[#777]">{title}</p>
      <p className="mt-2 text-xl font-semibold text-[#1a1a1a]">{value}</p>
      <p className={cn('mt-1 text-xs leading-5', terrain.muted)}>{description}</p>
    </div>
  )
}

function AnalyticsPatternDetailSkeleton() {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4" role="status">
      {Array.from({ length: 4 }).map((_, index) => (
        <TerrainCard key={index} className="p-4">
          <div className="h-4 w-24 rounded-full bg-[#E8E6DF]" />
          <div className="mt-3 h-8 w-20 rounded-full bg-[#E8E6DF]" />
          <div className="mt-3 h-3 w-full rounded-full bg-[#F0EFE9]" />
        </TerrainCard>
      ))}
    </div>
  )
}

function TrendSection({ data }: { data: AnalyticsPatternDetailResponse }) {
  const maxCount = Math.max(1, ...data.trend.map((bucket) => bucket.signal_count))

  return (
    <TerrainCard className="p-4">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold text-[#1a1a1a]">Tendance journalière</p>
        <p className={cn('text-xs leading-5', terrain.muted)}>
          Buckets backend en timezone {data.trend_timezone}.
        </p>
      </div>
      {data.trend.length === 0 ? (
        <TerrainEmptyState title="Aucune tendance disponible" className="mt-4" />
      ) : (
        <div className="mt-4 space-y-2">
          {data.trend.map((bucket) => (
            <div
              key={`${bucket.bucket_start}-${bucket.bucket_end}`}
              className="grid gap-2 text-sm md:grid-cols-[7rem_1fr_4rem]"
            >
              <span className={terrain.muted}>{formatBackendBucketDate(bucket.bucket_date)}</span>
              <div className="h-3 overflow-hidden rounded-full bg-[#F0EFE9]">
                <div
                  className="h-full rounded-full bg-[#114660]"
                  style={{ width: `${(bucket.signal_count / maxCount) * 100}%` }}
                />
              </div>
              <span className="font-semibold text-[#1a1a1a]">
                {formatNumber(bucket.signal_count)}
              </span>
            </div>
          ))}
        </div>
      )}
    </TerrainCard>
  )
}

function StatusDistributionSection({ data }: { data: AnalyticsPatternDetailResponse }) {
  return (
    <TerrainCard className="p-4">
      <p className="text-sm font-semibold text-[#1a1a1a]">Distribution par statut</p>
      {data.status_distribution.length === 0 ? (
        <TerrainEmptyState title="Aucun statut sur cette période" className="mt-4" />
      ) : (
        <div className="mt-4 space-y-2">
          {data.status_distribution.map((bucket) => (
            <div
              key={bucket.status}
              className="flex items-center justify-between rounded-xl border border-[#F0EFE9] bg-[#FBFAF7] px-3 py-2 text-sm"
            >
              <span className={terrain.muted}>{formatStatusLabel(bucket.status)}</span>
              <span className="font-semibold text-[#1a1a1a]">
                {formatNumber(bucket.signal_count)}
              </span>
            </div>
          ))}
        </div>
      )}
    </TerrainCard>
  )
}

function DistributionList({
  title,
  description,
  items,
  bucketCount,
  otherSignalCount,
}: {
  title: string
  description: string
  items: Array<{ id: string | null; name: string; signalCount: number }>
  bucketCount: number
  otherSignalCount: number
}) {
  return (
    <TerrainCard className="p-4">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold text-[#1a1a1a]">{title}</p>
        <p className={cn('text-xs leading-5', terrain.muted)}>{description}</p>
      </div>
      {items.length === 0 ? (
        <TerrainEmptyState title="Aucune donnée sur cette période" className="mt-4" />
      ) : (
        <div className="mt-4 space-y-2">
          {items.map((item) => (
            <div
              key={item.id ?? 'unassigned'}
              className="flex items-center justify-between gap-3 rounded-xl border border-[#F0EFE9] bg-[#FBFAF7] px-3 py-2 text-sm"
            >
              <span className="min-w-0 truncate text-[#1a1a1a]">{item.name}</span>
              <span className="shrink-0 font-semibold text-[#1a1a1a]">
                {formatNumber(item.signalCount)}
              </span>
            </div>
          ))}
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <Badge variant="outline" className="border-[#E8E6DF] bg-[#F7F6F2] text-[#555]">
          Buckets {formatNumber(bucketCount)}
        </Badge>
        <Badge variant="outline" className="border-[#E8E6DF] bg-[#F7F6F2] text-[#555]">
          Autres Signals {formatNumber(otherSignalCount)}
        </Badge>
      </div>
    </TerrainCard>
  )
}

function AnalyticsPatternDetailContent({
  data,
  onBack,
}: {
  data: AnalyticsPatternDetailResponse
  onBack: () => void
}) {
  return (
    <>
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <TerrainSectionLabel>Motif Analytics</TerrainSectionLabel>
          <h1 className="text-2xl font-semibold text-[#1a1a1a] md:text-3xl">
            {data.identity.label}
          </h1>
          <p className={cn('mt-1 text-sm', terrain.muted)}>
            {formatPeriod(data.current_period.period_start, data.current_period.period_end)}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge variant="outline" className="border-[#D8EADA] bg-[#F3FAF5] text-[#24614B]">
              {data.is_recurrent ? 'Récurrent' : 'Non récurrent'}
            </Badge>
            <Badge variant="outline" className="border-[#E8E6DF] bg-[#F7F6F2] text-[#555]">
              Statut {data.identity.status}
            </Badge>
          </div>
        </div>
        <Button type="button" variant="outline" onClick={onBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Retour aux motifs
        </Button>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Signals"
          value={formatNumber(data.metrics.signal_count)}
          description="Occurrences visibles dans la période."
          icon={Activity}
        />
        <MetricCard
          title="À traiter"
          value={formatNumber(data.metrics.actionable_signal_count)}
          description="Population actionable backend."
          icon={AlertCircle}
        />
        <MetricCard
          title="Dernière apparition"
          value={formatDateTime(data.metrics.last_seen_at)}
          description="Dernier Signal contributeur visible."
          icon={Clock3}
        />
        <MetricCard
          title="Établissements"
          value={formatNumber(data.metrics.establishment_count)}
          description="Établissements visibles contributeurs."
          icon={Building2}
        />
      </div>

      <TerrainCard className="p-4">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-[#114660]" aria-hidden />
            <p className="text-sm font-semibold text-[#1a1a1a]">Comparaison</p>
          </div>
          <p className={cn('text-xs leading-5', terrain.muted)}>
            Période précédente :{' '}
            {formatPeriod(data.previous_period.period_start, data.previous_period.period_end)}.
          </p>
          <ComparisonSummary comparison={data.metrics.signal_count_comparison} />
        </div>
      </TerrainCard>

      <TerrainCard className="p-4">
        <div className="flex items-center gap-2">
          <Repeat2 className="h-4 w-4 text-[#114660]" aria-hidden />
          <p className="text-sm font-semibold text-[#1a1a1a]">Récurrence</p>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <InlineMetric
            title="Occurrences 30j"
            value={formatNumber(data.occurrence_count_30d)}
            description="Fenêtre fixe backend."
          />
          <InlineMetric
            title="Jours distincts"
            value={formatNumber(data.distinct_day_count_30d)}
            description="Jours locaux par établissement."
          />
          <InlineMetric
            title="Fenêtre"
            value={formatPeriod(
              data.recurrence_window.window_start,
              data.recurrence_window.window_end,
            )}
            description={`Statut ${data.recurrence_status}.`}
          />
        </div>
      </TerrainCard>

      <TrendSection data={data} />

      <div className="grid gap-3 lg:grid-cols-2">
        <StatusDistributionSection data={data} />
        <DistributionList
          title="Établissements concernés"
          description="Résumé borné retourné par le backend."
          items={data.establishments.map((item) => ({
            id: item.establishment_id,
            name: item.name,
            signalCount: item.signal_count,
          }))}
          bucketCount={data.establishment_bucket_count}
          otherSignalCount={data.establishment_other_signal_count}
        />
      </div>

      <DistributionList
        title="BU responsables"
        description="Résumé borné des Business Units responsables."
        items={data.responsible_business_units.map((item) => ({
          id: item.business_unit_id,
          name: item.name,
          signalCount: item.signal_count,
        }))}
        bucketCount={data.business_unit_bucket_count}
        otherSignalCount={data.business_unit_other_signal_count}
      />
    </>
  )
}

export function AnalyticsPatternDetailPage({
  patternId,
  analyticsState,
  onNavigate,
}: AnalyticsPatternDetailPageProps) {
  const { bootstrap, isBootstrapping, isReady } = useAuth()
  const canAccessAnalytics = canShowAnalyticsNavigation(bootstrap)
  const detailQuery = useAnalyticsPatternDetailQuery(patternId, analyticsState, {
    enabled: isReady && !isBootstrapping && canAccessAnalytics,
  })
  const backPath = buildAnalyticsReturnPath(analyticsState)

  function navigateBack() {
    onNavigate(backPath)
  }

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

  const isNotFound =
    detailQuery.error instanceof AnalyticsApiError &&
    detailQuery.error.code === 'analytics_pattern_not_found'

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 px-3 pb-5 pt-3 md:px-5 lg:px-6">
      {detailQuery.isLoading ? <AnalyticsPatternDetailSkeleton /> : null}

      {detailQuery.isError ? (
        isNotFound ? (
          <TerrainEmptyState
            title="Motif introuvable"
            description="Ce motif est introuvable ou non accessible dans le contexte Analytics courant."
          />
        ) : (
          <TerrainErrorState
            message={resolveApiErrorMessage(
              detailQuery.error,
              AnalyticsApiError,
              'Impossible de charger ce motif.',
            )}
            onRetry={() => void detailQuery.refetch()}
          />
        )
      ) : null}

      {detailQuery.data ? (
        <AnalyticsPatternDetailContent data={detailQuery.data} onBack={navigateBack} />
      ) : null}
    </div>
  )
}
