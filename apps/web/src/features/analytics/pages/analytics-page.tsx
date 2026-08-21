import { Loader2 } from 'lucide-react'

import { useAppRoute } from '@/app/app-routes'
import type { TerrainScope } from '@/app/scoped-terrain'
import { useAuth } from '@/app/auth-provider'
import { TerrainEmptyState, TerrainErrorState } from '@/components/ui/terrain'
import { AnalyticsApiError } from '@/features/analytics/api'
import {
  ContributorsCard,
  DashboardAiSummaryPlaceholder,
  DashboardExportButton,
  DashboardRevenuePlaceholder,
  NewPatternsCard,
  ObservationTreatmentCard,
  OpenObservationsCard,
  PlanDeadlinesCard,
  PolesCard,
  RecurringPatternsCard,
  ZonesCard,
} from '@/features/analytics/components/dashboard-widgets'
import { useAnalyticsDashboardQuery } from '@/features/analytics/hooks'
import {
  collectDashboardComparisons,
  dashboardCoverageBannerMessage,
  worstDashboardCoverage,
} from '@/features/analytics/lib/dashboard-comparisons'
import {
  buildDashboardHref,
  DASHBOARD_PERIOD_DAYS,
  DEFAULT_DASHBOARD_PERIOD_DAYS,
  useDashboardPeriodDays,
  type DashboardPeriodDays,
} from '@/features/analytics/lib/dashboard-url-state'
import { canShowAnalyticsNavigation } from '@/features/navigation/lib/shared-navigation'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { cn } from '@/lib/utils'

type AnalyticsPageProps = {
  scope?: TerrainScope | { type: 'session' }
}

function resolveEstablishmentId(
  scope: AnalyticsPageProps['scope'],
  sessionEstablishmentId: string | null,
): string | null {
  if (!scope || scope.type === 'session') {
    return sessionEstablishmentId
  }
  if (scope.type === 'cross') {
    return null
  }
  return scope.establishmentId
}

function isEstablishmentAuthorized(
  establishmentId: string,
  memberships: Array<{ establishment_id: string; status: string }>,
): boolean {
  return memberships.some(
    (membership) =>
      membership.status === 'active' && membership.establishment_id === establishmentId,
  )
}

export function AnalyticsPage({ scope = { type: 'session' } }: AnalyticsPageProps) {
  const { navigate } = useAppRoute()
  const auth = useAuth()
  const periodDays = useDashboardPeriodDays()
  const canRead = canShowAnalyticsNavigation(auth.bootstrap)
  const sessionEstablishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const establishmentId = resolveEstablishmentId(scope, sessionEstablishmentId)
  const isCross = scope.type === 'cross'
  const scopedEstablishmentId = scope.type === 'establishment' ? scope.establishmentId : null
  const establishmentAllowed =
    scopedEstablishmentId == null ||
    isEstablishmentAuthorized(scopedEstablishmentId, auth.bootstrap?.memberships ?? [])

  const dashboardQuery = useAnalyticsDashboardQuery(
    { periodDays, establishmentId },
    { enabled: canRead && establishmentAllowed },
  )

  const pathname =
    scope.type === 'cross'
      ? '/cross'
      : scope.type === 'establishment'
        ? `/e/${scope.establishmentId}`
        : '/analytics'
  const coverageMessage = dashboardQuery.data
    ? dashboardCoverageBannerMessage({
        coverage: worstDashboardCoverage(collectDashboardComparisons(dashboardQuery.data)),
        historyReliableFrom: dashboardQuery.data.history_reliable_from,
      })
    : null

  function setPeriod(next: DashboardPeriodDays) {
    navigate(buildDashboardHref(pathname, next), { replace: true })
  }

  if (!canRead) {
    return (
      <TerrainEmptyState
        className="mx-4 mt-6"
        title="Accès refusé"
        description="Le Dashboard Analytics est réservé aux propriétaires, directeurs et managers."
      />
    )
  }

  if (!establishmentAllowed) {
    return (
      <TerrainEmptyState
        className="mx-4 mt-6"
        title="Accès refusé"
        description="Vous n’avez pas accès à cet établissement."
      />
    )
  }

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[96rem] flex-col gap-5 px-4 py-5 pb-10 lg:px-8 lg:py-6 lg:pb-12 xl:px-10">
      <header className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <h1 className="text-3xl font-bold tracking-tight text-[#1a1a1a]">Dashboard</h1>
          <p className="mt-1 text-sm text-[#7D7B75]">
            {isCross
              ? 'Vue agrégée de tous vos établissements'
              : 'Vue de l’établissement courant'}
          </p>
        </div>
        <div className="flex w-full min-w-0 flex-wrap items-center gap-2 lg:w-auto">
          <div className="flex min-w-0 flex-wrap gap-1 rounded-lg bg-white p-1 ring-1 ring-[#E8E6DF]">
            {DASHBOARD_PERIOD_DAYS.map((days) => (
              <button
                key={days}
                type="button"
                onClick={() => setPeriod(days)}
                className={cn(
                  'h-8 min-w-0 rounded-md px-2.5 text-[12px] font-semibold',
                  periodDays === days
                    ? 'bg-[#1F7A4D] text-white'
                    : 'text-[#7D7B75] hover:bg-[#F5F4F0]',
                )}
              >
                {days} j
              </button>
            ))}
          </div>
          <DashboardExportButton />
        </div>
      </header>

      {coverageMessage ? (
        <p className="rounded-xl border border-[#E8E6DF] bg-white px-4 py-2.5 text-[13px] text-[#7D7B75]">
          {coverageMessage}
        </p>
      ) : null}

      <DashboardAiSummaryPlaceholder />

      {dashboardQuery.isLoading ? (
        <div className="flex items-center justify-center py-16 text-[#7D7B75]">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : null}

      {dashboardQuery.isError ? (
        <TerrainErrorState
          message={
            dashboardQuery.error instanceof AnalyticsApiError &&
            dashboardQuery.error.status === 403
              ? 'Vous n’avez pas accès à cet établissement.'
              : resolveApiErrorMessage(
                  dashboardQuery.error,
                  AnalyticsApiError,
                  'Impossible de charger le dashboard.',
                )
          }
          onRetry={() => void dashboardQuery.refetch()}
        />
      ) : null}

      {dashboardQuery.data ? (
        <>
          <div className="grid min-w-0 gap-4 lg:grid-cols-2 lg:gap-5">
            <RecurringPatternsCard items={dashboardQuery.data.recurring_patterns} />
            <NewPatternsCard
              items={dashboardQuery.data.new_patterns}
              previewLimit={dashboardQuery.data.new_patterns_preview_limit}
              isCross={isCross}
            />
            <ContributorsCard items={dashboardQuery.data.contributors} />
            <ObservationTreatmentCard data={dashboardQuery.data} />
            <OpenObservationsCard data={dashboardQuery.data} />
            <PlanDeadlinesCard data={dashboardQuery.data} />
            <DashboardRevenuePlaceholder />
            <ZonesCard
              items={dashboardQuery.data.zones}
              previewLimit={dashboardQuery.data.zones_preview_limit}
              isCross={isCross}
            />
            <PolesCard items={dashboardQuery.data.poles} isCross={isCross} />
          </div>
        </>
      ) : null}
    </div>
  )
}

export { DEFAULT_DASHBOARD_PERIOD_DAYS }
