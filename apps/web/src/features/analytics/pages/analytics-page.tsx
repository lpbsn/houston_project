import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Filter,
  Loader2,
  Repeat2,
  Target,
  TrendingUp,
} from 'lucide-react'
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type SVGProps,
} from 'react'

import { useAuth } from '@/app/auth-provider'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  TerrainCard,
  TerrainEmptyState,
  TerrainErrorState,
  TerrainSectionLabel,
} from '@/components/ui/terrain'
import type { AnalyticsMetricComparison } from '@/features/analytics/api'
import { AnalyticsApiError } from '@/features/analytics/api'
import {
  useAnalyticsDashboardQuery,
  useAnalyticsPatternFilterOptionsQuery,
  useAnalyticsPatternsInfiniteQuery,
} from '@/features/analytics/hooks'
import {
  buildAnalyticsPath,
  buildAnalyticsPatternDetailPath,
  useAnalyticsUrlState,
  type AnalyticsRecurrenceFilter,
  type AnalyticsSignalStatusFilter,
  type AnalyticsUrlState,
} from '@/features/analytics/lib/analytics-url-state'
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

const PERIOD_PRESETS = [
  { days: 7, label: '7 jours' },
  { days: 30, label: '30 jours' },
  { days: 90, label: '90 jours' },
] as const

const RECURRENCE_OPTIONS: Array<{ value: AnalyticsRecurrenceFilter; label: string }> = [
  { value: 'all', label: 'Tous' },
  { value: 'recurrent', label: 'Récurrents' },
  { value: 'non_recurrent', label: 'Non récurrents' },
]

const SIGNAL_STATUS_OPTIONS: Array<{ value: AnalyticsSignalStatusFilter; label: string }> = [
  { value: 'open', label: 'Ouverts' },
  { value: 'in_progress', label: 'En cours' },
  { value: 'interesting', label: 'Intéressants' },
  { value: 'resolved', label: 'Résolus' },
  { value: 'archived', label: 'Archivés' },
]

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

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
  }).format(new Date(value))
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

function buildPresetState(state: AnalyticsUrlState, days: number): AnalyticsUrlState {
  const periodEnd = new Date(state.periodEnd)
  const periodStart = new Date(periodEnd)
  periodStart.setUTCDate(periodStart.getUTCDate() - days)
  return {
    ...state,
    periodStart: periodStart.toISOString(),
    periodEnd: periodEnd.toISOString(),
  }
}

function toggleString(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value].sort()
}

function AnalyticsGlobalPeriodControls({
  state,
  onStateChange,
}: {
  state: AnalyticsUrlState
  onStateChange: (state: AnalyticsUrlState, options?: { replace?: boolean }) => void
}) {
  return (
    <TerrainCard className="p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold text-[#1a1a1a]">Période Analytics</p>
          <p className={cn('mt-1 text-xs leading-5', terrain.muted)}>
            Contrôle global appliqué aux KPIs et à la liste des motifs.
          </p>
        </div>
        <div className="flex flex-wrap gap-2" aria-label="Période Analytics">
          {PERIOD_PRESETS.map((preset) => (
            <Button
              key={preset.days}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onStateChange(buildPresetState(state, preset.days))}
            >
              {preset.label}
            </Button>
          ))}
        </div>
      </div>
    </TerrainCard>
  )
}

function AnalyticsPatternFilters({
  state,
  onStateChange,
  filterOptions,
}: {
  state: AnalyticsUrlState
  onStateChange: (state: AnalyticsUrlState, options?: { replace?: boolean }) => void
  filterOptions:
    | {
        establishments: Array<{ establishment_id: string; name: string }>
        responsible_business_units: Array<{
          business_unit_id: string | null
          name: string
          is_unassigned: boolean
        }>
      }
    | undefined
}) {
  return (
    <TerrainCard className="p-4">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-[#114660]" aria-hidden />
          <p className="text-sm font-semibold text-[#1a1a1a]">Motifs</p>
        </div>
        <p className={cn('text-xs leading-5', terrain.muted)}>
          Filtres appliqués uniquement à la liste des motifs.
        </p>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1.2fr_1fr]">
        <label className="flex flex-col gap-1 text-xs font-semibold text-[#555]">
          Recherche motif
          <AnalyticsPatternSearchInput
            key={state.q}
            state={state}
            onStateChange={onStateChange}
          />
        </label>

        <label className="flex flex-col gap-1 text-xs font-semibold text-[#555]">
          Récurrence
          <select
            className="h-11 rounded-xl border border-border/70 bg-background/90 px-3 text-sm"
            value={state.recurrence}
            onChange={(event) =>
              onStateChange({
                ...state,
                recurrence: event.target.value as AnalyticsRecurrenceFilter,
              })
            }
          >
            {RECURRENCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <fieldset className="rounded-xl border border-[#F0EFE9] p-3">
          <legend className="px-1 text-xs font-semibold text-[#555]">Établissements</legend>
          <div className="mt-2 flex flex-col gap-2">
            {(filterOptions?.establishments ?? []).map((option) => (
              <label key={option.establishment_id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={state.establishmentIds.includes(option.establishment_id)}
                  onChange={() =>
                    onStateChange({
                      ...state,
                      establishmentIds: toggleString(
                        state.establishmentIds,
                        option.establishment_id,
                      ),
                    })
                  }
                />
                {option.name}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="rounded-xl border border-[#F0EFE9] p-3">
          <legend className="px-1 text-xs font-semibold text-[#555]">BU responsable</legend>
          <div className="mt-2 flex max-h-40 flex-col gap-2 overflow-y-auto">
            {(filterOptions?.responsible_business_units ?? []).map((option) => {
              if (option.is_unassigned) {
                return (
                  <label key="unassigned" className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={state.responsibleBusinessUnitUnassigned}
                      onChange={() =>
                        onStateChange({
                          ...state,
                          responsibleBusinessUnitUnassigned:
                            !state.responsibleBusinessUnitUnassigned,
                        })
                      }
                    />
                    {option.name}
                  </label>
                )
              }
              if (!option.business_unit_id) {
                return null
              }
              return (
                <label key={option.business_unit_id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={state.responsibleBusinessUnitIds.includes(option.business_unit_id)}
                    onChange={() =>
                      onStateChange({
                        ...state,
                        responsibleBusinessUnitIds: toggleString(
                          state.responsibleBusinessUnitIds,
                          option.business_unit_id!,
                        ),
                      })
                    }
                  />
                  {option.name}
                </label>
              )
            })}
          </div>
        </fieldset>

        <fieldset className="rounded-xl border border-[#F0EFE9] p-3">
          <legend className="px-1 text-xs font-semibold text-[#555]">Statuts Signal</legend>
          <div className="mt-2 flex flex-col gap-2">
            {SIGNAL_STATUS_OPTIONS.map((option) => (
              <label key={option.value} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={state.signalStatuses.includes(option.value)}
                  onChange={() =>
                    onStateChange({
                      ...state,
                      signalStatuses: toggleString(
                        state.signalStatuses,
                        option.value,
                      ) as AnalyticsSignalStatusFilter[],
                    })
                  }
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>
      </div>
    </TerrainCard>
  )
}

function AnalyticsPatternSearchInput({
  state,
  onStateChange,
}: {
  state: AnalyticsUrlState
  onStateChange: (state: AnalyticsUrlState, options?: { replace?: boolean }) => void
}) {
  const [draft, setDraft] = useState(state.q)
  const debounceRef = useRef<ReturnType<typeof window.setTimeout> | null>(null)

  function clearDebounce() {
    if (debounceRef.current) {
      window.clearTimeout(debounceRef.current)
      debounceRef.current = null
    }
  }

  function flush(nextValue = draft) {
    clearDebounce()
    onStateChange({ ...state, q: nextValue.trim() }, { replace: true })
  }

  function handleChange(value: string) {
    setDraft(value)
    clearDebounce()
    const scheduledSearch = window.location.search
    const nextState = { ...state, q: value.trim() }
    debounceRef.current = window.setTimeout(() => {
      if (window.location.search !== scheduledSearch) {
        return
      }
      onStateChange(nextState, { replace: true })
    }, 350)
  }

  useEffect(() => clearDebounce, [])

  return (
    <Input
      value={draft}
      placeholder="Nom du motif"
      onBlur={() => flush()}
      onChange={(event) => handleChange(event.target.value)}
      onKeyDown={(event) => {
        if (event.key === 'Enter') {
          flush()
        }
      }}
    />
  )
}

function AnalyticsPatternTable({
  query,
  state,
  onNavigate,
}: {
  query: ReturnType<typeof useAnalyticsPatternsInfiniteQuery>
  state: AnalyticsUrlState
  onNavigate?: (pathname: string, options?: { replace?: boolean }) => void
}) {
  const items = useMemo(
    () => query.data?.pages.flatMap((page) => page.items) ?? [],
    [query.data],
  )

  if (query.isLoading) {
    return (
      <TerrainCard className="p-4">
        <div className="flex items-center gap-2 text-sm text-[#555]" role="status">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        Chargement des motifs...
        </div>
      </TerrainCard>
    )
  }

  if (query.isError) {
    return (
      <TerrainErrorState
        message={resolveApiErrorMessage(
          query.error,
          AnalyticsApiError,
          'Impossible de charger les motifs.',
        )}
        onRetry={() => void query.refetch()}
      />
    )
  }

  if (items.length === 0) {
    return (
      <TerrainEmptyState
        title="Aucun motif visible"
        description="Aucun motif ne correspond aux filtres de liste sur cette période."
      />
    )
  }

  return (
    <TerrainCard className="overflow-hidden p-0">
      <div className="hidden grid-cols-[minmax(180px,1.5fr)_110px_120px_130px_140px_120px_minmax(160px,1fr)] gap-3 border-b border-[#F0EFE9] px-4 py-3 text-xs font-semibold uppercase tracking-[0.04em] text-[#777] lg:grid">
        <span>Motif</span>
        <span>Signals</span>
        <span>Évolution</span>
        <span>Récurrence</span>
        <span>Dernière apparition</span>
        <span>À traiter</span>
        <span>Établissements</span>
      </div>
      <div className="divide-y divide-[#F0EFE9]">
        {items.map((item) => {
          const detailPath = buildAnalyticsPatternDetailPath(item.pattern_id, state)

          return (
            <a
              key={item.pattern_id}
              href={detailPath}
              className="grid gap-3 px-4 py-4 text-sm transition-colors hover:bg-[#FBFAF7] focus:outline-none focus:ring-2 focus:ring-[#114660] focus:ring-offset-2 lg:grid-cols-[minmax(180px,1.5fr)_110px_120px_130px_140px_120px_minmax(160px,1fr)]"
              onClick={(event) => {
                if (
                  !onNavigate ||
                  event.metaKey ||
                  event.ctrlKey ||
                  event.shiftKey ||
                  event.altKey
                ) {
                  return
                }
                event.preventDefault()
                onNavigate(detailPath)
              }}
            >
              <div>
                <p className="font-semibold text-[#1a1a1a]">{item.label}</p>
                <p className={cn('text-xs', terrain.muted)}>{item.normalized_label}</p>
              </div>
              <p>
                <span className="lg:hidden">Signals: </span>
                {formatNumber(item.signal_count)}
              </p>
              <p>
                <span className="lg:hidden">Évolution: </span>
                {formatAbsoluteDelta(item.signal_count_comparison.absolute_delta, formatNumber)}
              </p>
              <p>
                <span className="lg:hidden">Récurrence: </span>
                {item.is_recurrent ? 'Oui' : 'Non'} ({item.occurrence_count_30d}/
                {item.distinct_day_count_30d}j)
              </p>
              <p>
                <span className="lg:hidden">Dernière apparition: </span>
                {formatDateTime(item.last_seen_at)}
              </p>
              <p>
                <span className="lg:hidden">À traiter: </span>
                {formatNumber(item.actionable_signal_count)}
              </p>
              <p className="text-[#555]">
                <span className="lg:hidden">Établissements: </span>
                {item.establishments.map((establishment) => establishment.name).join(', ') || '—'}
                {item.establishment_count > item.establishments.length
                  ? ` +${item.establishment_count - item.establishments.length}`
                  : ''}
              </p>
            </a>
          )
        })}
      </div>
      {query.hasNextPage ? (
        <div className="border-t border-[#F0EFE9] p-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => void query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
          >
            {query.isFetchingNextPage ? 'Chargement...' : 'Charger plus'}
          </Button>
        </div>
      ) : null}
    </TerrainCard>
  )
}

type AnalyticsPageProps = {
  onNavigate?: (pathname: string, options?: { replace?: boolean }) => void
}

export function AnalyticsPage({ onNavigate }: AnalyticsPageProps) {
  const { bootstrap, isBootstrapping, isReady } = useAuth()
  const analyticsState = useAnalyticsUrlState()
  const canAccessAnalytics = canShowAnalyticsNavigation(bootstrap)
  const dashboardQuery = useAnalyticsDashboardQuery(analyticsState, {
    enabled: isReady && !isBootstrapping && canAccessAnalytics,
  })
  const patternsQuery = useAnalyticsPatternsInfiniteQuery(analyticsState, {
    enabled: isReady && !isBootstrapping && canAccessAnalytics,
  })
  const filterOptionsQuery = useAnalyticsPatternFilterOptionsQuery(analyticsState, {
    enabled: isReady && !isBootstrapping && canAccessAnalytics,
  })

  function updateAnalyticsState(nextState: AnalyticsUrlState, options?: { replace?: boolean }) {
    const href = buildAnalyticsPath(nextState)
    const method = options?.replace ? 'replaceState' : 'pushState'
    window.history[method](null, '', href)
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

          <AnalyticsGlobalPeriodControls
            state={analyticsState}
            onStateChange={updateAnalyticsState}
          />

          <AnalyticsPatternFilters
            state={analyticsState}
            onStateChange={updateAnalyticsState}
            filterOptions={filterOptionsQuery.data}
          />

          <AnalyticsPatternTable
            query={patternsQuery}
            state={analyticsState}
            onNavigate={onNavigate}
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
