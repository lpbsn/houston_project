import { useMemo, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, LoaderCircle, Plus } from 'lucide-react'

import { serializeAppRoute, useAppRoute } from '@/app/app-routes'
import { serializeScopedExecutionDetailPath } from '@/app/scoped-terrain'
import { useAuth } from '@/app/auth-provider'
import { getBootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubTitleSlot } from '@/components/layout/terrain-hub-title-slot'
import { TerrainHubViewToolbar } from '@/components/layout/terrain-hub-view-toolbar'
import { Button } from '@/components/ui/button'
import {
  TerrainEmptyState,
  TerrainErrorState,
  TerrainCollapsibleFeedSection,
  TerrainSegmentedControl,
} from '@/components/ui/terrain'
import { useCollapsibleFeedSections } from '@/lib/use-collapsible-feed-sections'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'
import { ActionPlansApiError, unwrapActionPlanExecutionFeedItems } from '@/features/action-plans/api'
import {
  useActionPlanExecutionCalendarQuery,
  useActionPlanExecutionFeedQuery,
} from '@/features/action-plans/hooks'
import type { ActionPlanExecutionFeedResponse } from '@/features/action-plans/types'

import { ActionPlanExecutionFeedCard } from '../components/action-plan-execution-feed-card'
import { ExecutionCalendarView } from '../components/execution-calendar-view'
import { ExecutionCreateMenuSheet } from '../components/execution-create-menu-sheet'
import { ExecutionFeedTabs } from '../components/execution-feed-tabs'
import { ExecutionUpcomingNavRow } from '../components/execution-upcoming-nav-row'
import {
  appendExecutionFeedSearch,
  executionFeedHref,
  parseExecutionFeedSearch,
  type ExecutionCalendarGranularity,
  type ExecutionFeedLayout,
} from '../lib/execution-feed-url-state'
import { ActionPlanExecutionFeedCardActionsSheet } from '@/features/action-plans/components/action-plan-execution-feed-card-actions-sheet'
import { useActionPlanExecutionFeedQuickActions } from '@/features/action-plans/hooks/use-action-plan-execution-feed-quick-actions'
import {
  groupActionPlanExecutionsBySection,
  partitionActionPlanExecutionFeedPinnedItems,
} from '../lib/action-plan-execution-feed-sections'
import { canOpenExecutionCreateMenu } from '../lib/execution-create-menu'
import { getEmptyFeedDescription } from '../lib/execution-feed-empty'
import {
  calendarAnchorToday,
  calendarTimezoneScopeKey,
  formatCalendarPeriodLabel,
  rememberScopedCalendarTimezone,
  resolveCalendarWindow,
  resolveScopedCalendarTimezone,
  shiftCalendarAnchor,
  type RememberedCalendarTimezone,
} from '../lib/execution-calendar-window'

const EXECUTION_FEED_DEFAULT_COLLAPSED_SECTIONS = ['done', 'canceled'] as const

type ExecutionFeedPageProps = {
  onOpenActionPlanExecution?: (executionId: string) => void
  onNavigate?: (pathname: string) => void
  establishmentId?: string | null
  source?: 'establishment' | 'cross'
}

function readScheduledCountFromFeedPages(
  pages: ActionPlanExecutionFeedResponse[] | undefined,
): number {
  if (!pages?.length) {
    return 0
  }

  const pageWithScheduled =
    pages.find((page) => typeof page.scheduled_count === 'number') ?? pages[0]

  return pageWithScheduled?.scheduled_count ?? 0
}

export function ExecutionFeedPage({
  onNavigate,
  establishmentId: establishmentIdProp,
  source = 'establishment',
}: ExecutionFeedPageProps) {
  const auth = useAuth()
  const { route, search, navigate } = useAppRoute()
  const establishmentId =
    establishmentIdProp ?? auth.bootstrap?.active_membership?.establishment_id ?? null
  const isCross = source === 'cross'
  const feedUrlOptions = isCross
    ? { defaultViewMode: 'general' as const }
    : undefined
  const feedUrl = parseExecutionFeedSearch(search, new Date(), feedUrlOptions)
  const viewMode = feedUrl.viewMode
  const layout: ExecutionFeedLayout = feedUrl.layout
  const granularity = feedUrl.granularity
  const calendarWindow = useMemo(
    () => resolveCalendarWindow(granularity, feedUrl.anchor),
    [granularity, feedUrl.anchor],
  )
  const [isCreateMenuOpen, setIsCreateMenuOpen] = useState(false)

  function replaceFeedUrl(
    patch: Partial<{
      layout: ExecutionFeedLayout
      granularity: ExecutionCalendarGranularity
      anchor: string
      viewMode: typeof viewMode
    }>,
  ) {
    const pathname = serializeAppRoute(route).split('?')[0] || '/execution'
    navigate(
      executionFeedHref(
        pathname,
        {
          ...feedUrl,
          ...patch,
        },
        feedUrlOptions,
      ),
      { replace: true },
    )
  }

  const planFeedQuery = useActionPlanExecutionFeedQuery(establishmentId, viewMode, { source })
  const calendarQuery = useActionPlanExecutionCalendarQuery(
    establishmentId,
    viewMode,
    { from: calendarWindow.from, to: calendarWindow.to },
    { enabled: layout === 'calendar', source },
  )
  const calendarTimezoneScope = calendarTimezoneScopeKey(source, establishmentId)
  const rememberedCalendarTimezoneRef = useRef<RememberedCalendarTimezone | null>(null)
  rememberedCalendarTimezoneRef.current = rememberScopedCalendarTimezone(
    rememberedCalendarTimezoneRef.current,
    calendarTimezoneScope,
    calendarQuery.data?.timezone,
  )
  const calendarTimeZone = resolveScopedCalendarTimezone(
    rememberedCalendarTimezoneRef.current,
    calendarQuery.data?.timezone,
  )
  const quickActions = useActionPlanExecutionFeedQuickActions({
    establishmentId,
    viewMode,
  })

  const planItems = planFeedQuery.isSuccess
    ? unwrapActionPlanExecutionFeedItems(planFeedQuery.data.pages.flatMap((page) => page.items))
    : []
  const scheduledCount = planFeedQuery.isSuccess
    ? readScheduledCountFromFeedPages(planFeedQuery.data.pages)
    : 0
  const { pinnedItems, unpinnedItems } = partitionActionPlanExecutionFeedPinnedItems(planItems)
  const planGroups = groupActionPlanExecutionsBySection(unpinnedItems)
  const sectionKeys = planGroups.map((group) => group.section)
  const { isExpanded, toggle } = useCollapsibleFeedSections(sectionKeys, {
    defaultCollapsedKeys: EXECUTION_FEED_DEFAULT_COLLAPSED_SECTIONS,
    resetToken: viewMode,
  })

  const permissionHints = auth.bootstrap
    ? getBootstrapPermissionHints(auth.bootstrap)
    : null
  const canCreate =
    !isCross &&
    auth.bootstrap != null &&
    !auth.isBootstrapping &&
    canOpenExecutionCreateMenu(permissionHints)

  const isInitialLoading = planFeedQuery.isLoading
  const showGlobalEmpty =
    planItems.length === 0 &&
    scheduledCount === 0 &&
    planFeedQuery.isSuccess &&
    !planFeedQuery.isLoading
  const hasVisibleItems = pinnedItems.length > 0 || planGroups.length > 0
  const hasMore = planFeedQuery.hasNextPage
  const isFetchingMore = planFeedQuery.isFetchingNextPage

  const createAction = canCreate ? (
    <Button
      type="button"
      size="icon"
      className={cn(
        'h-10 w-10 min-h-10 min-w-10 shrink-0 rounded-xl text-white',
        terrainBrandAction.bg,
        terrainBrandAction.hover,
      )}
      aria-label="Créer"
      onClick={() => setIsCreateMenuOpen(true)}
    >
      <Plus className="h-5 w-5" />
    </Button>
  ) : null

  function executionDetailPath(executionId: string): string {
    if (route.kind === 'scoped-terrain') {
      return serializeScopedExecutionDetailPath(route.scope, executionId)
    }
    if (isCross) {
      return `/cross/execution/${executionId}`
    }
    return `/action-plans/executions/${executionId}`
  }

  function openExecution(executionId: string) {
    navigate(
      appendExecutionFeedSearch(executionDetailPath(executionId), search, feedUrlOptions),
    )
  }

  if (!establishmentId && !isCross) {
    return (
      <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ExecutionCreateMenuSheet
        open={isCreateMenuOpen}
        permissionHints={permissionHints ?? undefined}
        onClose={() => setIsCreateMenuOpen(false)}
        onSelectActionPlan={() => onNavigate?.('/action-plans/new?from=execution')}
        onSelectCatalog={() => onNavigate?.('/action-plans')}
      />
      <TerrainHubTitleSlot>
        <ExecutionFeedTabs
          viewMode={viewMode}
          onChange={(next) => replaceFeedUrl({ viewMode: next })}
        />
      </TerrainHubTitleSlot>
      <TerrainHubSubheader>
        <div className="flex flex-col gap-2">
          <TerrainHubViewToolbar className="pb-3 pt-3" trailing={createAction}>
            <TerrainSegmentedControl
              ariaLabel="Disposition du feed"
              className="w-fit"
              value={layout}
              onChange={(next) => replaceFeedUrl({ layout: next })}
              options={[
                { value: 'list', label: 'Liste' },
                { value: 'calendar', label: 'Calendrier' },
              ]}
            />
          </TerrainHubViewToolbar>
          {layout === 'calendar' ? (
            <CalendarPeriodToolbar
              granularity={granularity}
              periodLabel={formatCalendarPeriodLabel(granularity, calendarWindow, feedUrl.anchor)}
              onGranularityChange={(next) => replaceFeedUrl({ granularity: next })}
              onPrevious={() =>
                replaceFeedUrl({
                  anchor: shiftCalendarAnchor(granularity, feedUrl.anchor, -1),
                })
              }
              onToday={() => replaceFeedUrl({ anchor: calendarAnchorToday(calendarTimeZone) })}
              onNext={() =>
                replaceFeedUrl({
                  anchor: shiftCalendarAnchor(granularity, feedUrl.anchor, 1),
                })
              }
            />
          ) : null}
        </div>
      </TerrainHubSubheader>
      <div
        className={cn(
          'min-h-0 flex-1 px-3 pb-4',
          layout === 'calendar'
            ? 'flex flex-col overflow-hidden'
            : 'overflow-y-auto overscroll-y-contain',
        )}
      >
        {layout === 'calendar' ? (
          <div className="flex min-h-0 flex-1 flex-col pt-3">
            <ExecutionCalendarView
              granularity={granularity}
              days={calendarWindow.days}
              month={feedUrl.anchor.slice(0, 7)}
              data={calendarQuery.data}
              timeZone={calendarTimeZone}
              isLoading={calendarQuery.isLoading}
              isError={calendarQuery.isError}
              error={calendarQuery.error}
              onRetry={() => void calendarQuery.refetch()}
              onOpenExecution={openExecution}
            />
          </div>
        ) : (
          <>
        {isInitialLoading ? (
          <div className="flex items-center justify-center py-16 text-[#7D7B75]">
            <LoaderCircle className="h-6 w-6 animate-spin" />
          </div>
        ) : null}

        {!isInitialLoading ? (
          <div className="flex flex-col gap-3 pt-5">
            {planFeedQuery.isError ? (
              <TerrainErrorState
                message={resolveApiErrorMessage(
                  planFeedQuery.error,
                  ActionPlansApiError,
                  'Impossible de charger les plans d’action.',
                )}
                onRetry={() => void planFeedQuery.refetch()}
              />
            ) : null}

            {planFeedQuery.isSuccess && onNavigate && !isCross ? (
              <ExecutionUpcomingNavRow
                count={scheduledCount}
                onNavigate={() => onNavigate('/execution/upcoming')}
              />
            ) : null}

            {planFeedQuery.isSuccess && hasVisibleItems ? (
              <>
                {pinnedItems.length > 0 ? (
                  <div className="flex flex-col gap-3">
                    {pinnedItems.map((item) => (
                      <ActionPlanExecutionFeedCard
                        key={`plan-pinned-${item.id}`}
                        item={item}
                        onSelect={openExecution}
                        onOpenActions={isCross ? undefined : quickActions.openActions}
                      />
                    ))}
                  </div>
                ) : null}

                {planGroups.length > 0 ? (
                  <div className="flex flex-col gap-2">
                    {planGroups.map((group) => (
                      <TerrainCollapsibleFeedSection
                        key={`plan-${group.section}`}
                        label={group.label}
                        count={group.items.length}
                        dotVariant={group.dotVariant}
                        expanded={isExpanded(group.section)}
                        onToggle={() => toggle(group.section)}
                      >
                        <div className="flex flex-col gap-3">
                          {group.items.map((item) => (
                            <ActionPlanExecutionFeedCard
                              key={`plan-${item.id}`}
                              item={item}
                              onSelect={openExecution}
                              onOpenActions={isCross ? undefined : quickActions.openActions}
                            />
                          ))}
                        </div>
                      </TerrainCollapsibleFeedSection>
                    ))}
                  </div>
                ) : null}
              </>
            ) : null}

            {showGlobalEmpty ? (
              <TerrainEmptyState
                className="mx-3 mt-3"
                title="Aucune exécution"
                description={getEmptyFeedDescription(
                  viewMode,
                  auth.bootstrap?.active_membership?.role,
                )}
              />
            ) : null}

            {hasMore ? (
              <div className="flex justify-center py-4">
                <button
                  type="button"
                  className="text-xs font-semibold text-[#1B4FD8] disabled:opacity-60"
                  onClick={() => void planFeedQuery.fetchNextPage()}
                  disabled={isFetchingMore}
                >
                  {isFetchingMore ? 'Chargement…' : 'Charger plus'}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
          </>
        )}
      </div>

      {quickActions.activeItem ? (
        <ActionPlanExecutionFeedCardActionsSheet
          item={quickActions.activeItem}
          open={quickActions.actionsOpen}
          isPending={quickActions.isPending}
          onClose={quickActions.closeActions}
          onSelectAction={quickActions.runAction}
        />
      ) : null}
    </div>
  )
}

function CalendarPeriodToolbar({
  granularity,
  periodLabel,
  onGranularityChange,
  onPrevious,
  onToday,
  onNext,
}: {
  granularity: ExecutionCalendarGranularity
  periodLabel: string
  onGranularityChange: (value: ExecutionCalendarGranularity) => void
  onPrevious: () => void
  onToday: () => void
  onNext: () => void
}) {
  const granularityControl = (
    <TerrainSegmentedControl
      ariaLabel="Granularité du calendrier"
      value={granularity}
      onChange={onGranularityChange}
      options={[
        { value: 'day', label: 'Jour' },
        { value: 'week', label: 'Semaine' },
        { value: 'month', label: 'Mois' },
      ]}
    />
  )
  const nav = (
    <div className="flex shrink-0 items-center gap-1">
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="h-8 w-8"
        aria-label="Période précédente"
        onClick={onPrevious}
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <Button type="button" variant="outline" size="sm" className="h-8" onClick={onToday}>
        Aujourd’hui
      </Button>
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="h-8 w-8"
        aria-label="Période suivante"
        onClick={onNext}
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  )

  return (
    <div className="px-3 pb-2">
      <div className="flex flex-wrap items-center gap-2 lg:grid lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
        <p className="min-w-0 flex-1 truncate text-sm font-semibold capitalize text-[#1a1a1a]">
          {periodLabel}
        </p>
        <div className="order-3 w-full lg:order-none lg:w-auto lg:justify-self-center">
          {granularityControl}
        </div>
        <div className="ml-auto lg:ml-0 lg:justify-self-end">{nav}</div>
      </div>
    </div>
  )
}
