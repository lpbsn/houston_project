import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'

import { serializeAppRoute, useAppRoute } from '@/app/app-routes'
import { serializeScopedExecutionDetailPath } from '@/app/scoped-terrain'
import { useAuth } from '@/app/auth-provider'
import { getBootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { useLgViewport } from '@/lib/lg-viewport'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubTitleSlot } from '@/components/layout/terrain-hub-title-slot'
import { TerrainHubViewToolbar } from '@/components/layout/terrain-hub-view-toolbar'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
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
import {
  ActionPlansApiError,
  unwrapActionPlanExecutionFeedItems,
} from '@/features/action-plans/api'
import {
  useActionPlanExecutionCalendarQuery,
  useActionPlanExecutionFeedQuery,
} from '@/features/action-plans/hooks'
import type {
  ActionPlanExecutionFeedResponse,
  ActionPlanExecutionFeedSectionCounts,
} from '@/features/action-plans/types'
import { useActionPlanExecutionFeedQuickActions } from '@/features/action-plans/hooks/use-action-plan-execution-feed-quick-actions'

import { ActionPlanExecutionFeedCard } from '../components/action-plan-execution-feed-card'
import { ActionPlanExecutionFeedDesktopRow } from '../components/action-plan-execution-feed-desktop-row'
import { ExecutionCalendarView } from '../components/execution-calendar-view'
import { ExecutionCreateMenuSheet } from '../components/execution-create-menu-sheet'
import { ExecutionFeedTabs } from '../components/execution-feed-tabs'
import { ExecutionFeedSkeletonList } from '../components/execution-feed-skeleton'
import { ExecutionPlanifieesNavRow } from '../components/execution-planifiees-nav-row'
import {
  appendExecutionFeedSearch,
  executionFeedHref,
  parseExecutionFeedSearch,
  type ExecutionCalendarGranularity,
  type ExecutionFeedLayout,
} from '../lib/execution-feed-url-state'
import {
  EXECUTION_FEED_DEFAULT_COLLAPSED_SECTIONS,
  EXECUTION_FEED_PINNED_SECTION_KEY,
  groupActionPlanExecutionsBySection,
  hasActionPlanExecutionFeedSections,
  partitionActionPlanExecutionFeedPinnedItems,
  type ActionPlanExecutionFeedSectionKey,
} from '../lib/action-plan-execution-feed-sections'
import { formatPlanifieesProchaineLabel } from '../lib/action-plan-execution-feed-card-display'
import { canOpenExecutionCreateMenu } from '../lib/execution-create-menu'
import {
  executionFeedReadingScopeKey,
  readExecutionFeedReading,
  writeExecutionFeedReading,
} from '../lib/execution-feed-reading-memory'
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

type ExecutionFeedPageProps = {
  onNavigate?: (pathname: string) => void
  establishmentId?: string | null
  source?: 'establishment' | 'cross'
}

const EMPTY_SECTION_COUNTS: ActionPlanExecutionFeedSectionCounts = {
  pinned: 0,
  pending_validation: 0,
  overdue: 0,
  in_progress: 0,
  done: 0,
  canceled: 0,
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

function readFirstScheduledItemFromFeedPages(
  pages: ActionPlanExecutionFeedResponse[] | undefined,
) {
  if (!pages?.length) {
    return null
  }
  const page =
    pages.find((entry) => (entry.scheduled_items?.length ?? 0) > 0) ?? pages[0]
  const wrapper = page?.scheduled_items?.[0]
  return wrapper?.action_plan_execution ?? null
}

function readSectionCountsFromFeedPages(
  pages: ActionPlanExecutionFeedResponse[] | undefined,
): ActionPlanExecutionFeedSectionCounts {
  if (!pages?.length) {
    return EMPTY_SECTION_COUNTS
  }
  const page = pages.find((entry) => entry.section_counts) ?? pages[0]
  return page?.section_counts ?? EMPTY_SECTION_COUNTS
}

/**
 * Remount when the reading scope changes so list scroll/sections of establishment A
 * cannot leak into B (or Cross) when `/execution` stays mounted across a switch.
 */
export function ExecutionFeedPage({
  onNavigate,
  establishmentId: establishmentIdProp,
  source = 'establishment',
}: ExecutionFeedPageProps) {
  const auth = useAuth()
  const establishmentId =
    establishmentIdProp ?? auth.bootstrap?.active_membership?.establishment_id ?? null
  const readingScopeKey = executionFeedReadingScopeKey(source, establishmentId)
  return (
    <ExecutionFeedPageContent
      key={readingScopeKey}
      onNavigate={onNavigate}
      establishmentId={establishmentId}
      source={source}
    />
  )
}

function ExecutionFeedPageContent({
  onNavigate,
  establishmentId,
  source,
}: {
  onNavigate?: (pathname: string) => void
  establishmentId: string | null
  source: 'establishment' | 'cross'
}) {
  const auth = useAuth()
  const { route, search, navigate } = useAppRoute()
  const isCross = source === 'cross'
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const readingScopeKey = executionFeedReadingScopeKey(source, establishmentId)
  const [initialReading] = useState(() => readExecutionFeedReading(readingScopeKey))
  const scrollRef = useRef<HTMLDivElement>(null)
  const restoredScrollRef = useRef(false)
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
  const [rememberedCalendarTimezone, setRememberedCalendarTimezone] =
    useState<RememberedCalendarTimezone | null>(null)
  const nextRemembered = rememberScopedCalendarTimezone(
    rememberedCalendarTimezone,
    calendarTimezoneScope,
    calendarQuery.data?.timezone,
  )
  if (
    nextRemembered?.scopeKey !== rememberedCalendarTimezone?.scopeKey ||
    nextRemembered?.timezone !== rememberedCalendarTimezone?.timezone
  ) {
    setRememberedCalendarTimezone(nextRemembered)
  }
  const calendarTimeZone = resolveScopedCalendarTimezone(
    nextRemembered,
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
  const nextScheduledPreview = planFeedQuery.isSuccess
    ? readFirstScheduledItemFromFeedPages(planFeedQuery.data.pages)
    : null
  const prochaineLabel = formatPlanifieesProchaineLabel(nextScheduledPreview)
  const sectionCounts = planFeedQuery.isSuccess
    ? readSectionCountsFromFeedPages(planFeedQuery.data.pages)
    : EMPTY_SECTION_COUNTS
  const { pinnedItems, unpinnedItems } = partitionActionPlanExecutionFeedPinnedItems(planItems)
  const planGroups = groupActionPlanExecutionsBySection(unpinnedItems, sectionCounts)
  const hasVisibleSections = hasActionPlanExecutionFeedSections(sectionCounts)

  const sectionKeys = useMemo((): string[] => {
    const keys: string[] = []
    if (sectionCounts.pinned > 0) {
      keys.push(EXECUTION_FEED_PINNED_SECTION_KEY)
    }
    for (const group of planGroups) {
      keys.push(group.section)
    }
    return keys
  }, [sectionCounts.pinned, planGroups])

  const savedMatchesView = initialReading?.viewMode === viewMode
  const { isExpanded, toggle, expandedByKey } = useCollapsibleFeedSections(sectionKeys, {
    defaultCollapsedKeys: EXECUTION_FEED_DEFAULT_COLLAPSED_SECTIONS,
    resetToken: viewMode,
    initialExpandedByKey: savedMatchesView ? initialReading?.expandedByKey : undefined,
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
    !hasVisibleSections &&
    scheduledCount === 0 &&
    planFeedQuery.isSuccess &&
    !planFeedQuery.isLoading
  const hasMore = planFeedQuery.hasNextPage
  const isFetchingMore = planFeedQuery.isFetchingNextPage
  const canRememberReading = Boolean(establishmentId) || isCross
  const savedScrollTop = savedMatchesView ? (initialReading?.scrollTop ?? 0) : 0

  function sectionCountFor(
    key: typeof EXECUTION_FEED_PINNED_SECTION_KEY | ActionPlanExecutionFeedSectionKey,
  ): number {
    return sectionCounts[key]
  }

  const planifieesHref = isCross ? '/cross/execution/upcoming' : '/execution/upcoming'

  useLayoutEffect(() => {
    if (restoredScrollRef.current || layout !== 'list') {
      return
    }
    const scroller = scrollRef.current
    if (!scroller) {
      return
    }
    if (savedScrollTop > 0 && !planFeedQuery.isSuccess) {
      return
    }
    scroller.scrollTop = savedScrollTop
    restoredScrollRef.current = true
  }, [layout, planFeedQuery.isSuccess, savedScrollTop])

  useEffect(() => {
    if (!canRememberReading) {
      return
    }
    writeExecutionFeedReading(readingScopeKey, {
      viewMode,
      expandedByKey,
      scrollTop:
        layout === 'list' && restoredScrollRef.current
          ? (scrollRef.current?.scrollTop ?? 0)
          : savedScrollTop,
    })
  }, [canRememberReading, expandedByKey, layout, readingScopeKey, savedScrollTop, viewMode])

  const createAction = canCreate ? (
    isDesktopWeb ? (
      <Button
        type="button"
        className={cn(
          'h-9 shrink-0 rounded-lg px-3 text-sm font-semibold text-white',
          terrainBrandAction.bg,
          terrainBrandAction.hover,
        )}
        onClick={() => setIsCreateMenuOpen(true)}
      >
        Créer
      </Button>
    ) : (
      <Button
        type="button"
        size="icon"
        variant="ghost"
        className={cn(
          // Visual disc is size-7; -m-2 keeps a ~44px tap target without growing the toolbar row.
          '-m-2 size-11 min-h-11 min-w-11 shrink-0 rounded-none border-0 bg-transparent p-0',
          'text-white shadow-none hover:bg-transparent',
        )}
        aria-label="Créer"
        onClick={() => setIsCreateMenuOpen(true)}
      >
        <span
          className={cn(
            'inline-flex size-7 items-center justify-center rounded-xl',
            terrainBrandAction.bg,
            'group-hover/button:bg-[#0f3d52]',
          )}
          aria-hidden
        >
          <Plus className="size-3.5" strokeWidth={1.75} />
        </span>
      </Button>
    )
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

  function renderFeedItem(item: (typeof planItems)[number], keyPrefix: string) {
    if (isDesktopWeb) {
      return (
        <ActionPlanExecutionFeedDesktopRow
          key={`${keyPrefix}-${item.id}`}
          item={item}
          onSelect={openExecution}
          onTogglePin={
            isCross
              ? undefined
              : (feedItem) => {
                  quickActions.clearActionError()
                  quickActions.runAction('pin', feedItem)
                }
          }
        />
      )
    }
    return (
      <ActionPlanExecutionFeedCard
        key={`${keyPrefix}-${item.id}`}
        item={item}
        onSelect={openExecution}
        onTogglePin={
          isCross
            ? undefined
            : (feedItem) => {
                quickActions.clearActionError()
                quickActions.runAction('pin', feedItem)
              }
        }
      />
    )
  }

  if (!establishmentId && !isCross) {
    return (
      <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
    )
  }

  const viewTabs = (
    <ExecutionFeedTabs
      viewMode={viewMode}
      onChange={(next) => replaceFeedUrl({ viewMode: next })}
      size={isDesktopWeb ? 'default' : 'compact'}
    />
  )

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ExecutionCreateMenuSheet
        open={isCreateMenuOpen}
        presentation={isDesktopWeb ? 'dialog' : 'sheet'}
        permissionHints={permissionHints ?? undefined}
        onClose={() => setIsCreateMenuOpen(false)}
        onSelectActionPlan={() => onNavigate?.('/action-plans/new?from=execution')}
        onSelectCatalog={() => onNavigate?.('/action-plans')}
      />
      <TerrainHubTitleSlot>{viewTabs}</TerrainHubTitleSlot>
      <TerrainHubSubheader>
        <div className={cn('flex flex-col', isDesktopWeb ? 'gap-2' : 'gap-0')}>
          <TerrainHubViewToolbar
            className={isDesktopWeb ? 'pb-3 pt-3' : 'pb-0.5 pt-0'}
            trailing={createAction}
          >
            <TerrainSegmentedControl
              ariaLabel="Disposition du feed"
              className="w-fit"
              size={isDesktopWeb ? 'default' : 'compact'}
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
        ref={scrollRef}
        data-testid="execution-feed-scroll"
        className={cn(
          'min-h-0 flex-1 px-3 pb-4',
          layout === 'calendar'
            ? 'flex flex-col overflow-hidden'
            : 'overflow-y-auto overscroll-y-contain',
        )}
        onScroll={(event) => {
          if (!canRememberReading || layout !== 'list' || !restoredScrollRef.current) {
            return
          }
          writeExecutionFeedReading(readingScopeKey, {
            viewMode,
            scrollTop: event.currentTarget.scrollTop,
          })
        }}
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
            {isInitialLoading ? <ExecutionFeedSkeletonList /> : null}

            {!isInitialLoading ? (
              <div className="flex flex-col gap-3 pt-5">
                {!isCross && quickActions.actionError ? (
                  <TerrainFeedback variant="error" message={quickActions.actionError} />
                ) : null}

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

                {planFeedQuery.isSuccess && onNavigate && scheduledCount > 0 ? (
                  <ExecutionPlanifieesNavRow
                    count={scheduledCount}
                    prochaineLabel={prochaineLabel}
                    onNavigate={() => onNavigate(planifieesHref)}
                  />
                ) : null}

                {planFeedQuery.isSuccess && hasVisibleSections ? (
                  <>
                    {sectionCounts.pinned > 0 ? (
                      <TerrainCollapsibleFeedSection
                        key="plan-pinned"
                        label="Épinglés"
                        count={sectionCountFor(EXECUTION_FEED_PINNED_SECTION_KEY)}
                        expanded={isExpanded(EXECUTION_FEED_PINNED_SECTION_KEY)}
                        onToggle={() => toggle(EXECUTION_FEED_PINNED_SECTION_KEY)}
                      >
                        <div
                          className={
                            isDesktopWeb ? 'flex flex-col gap-1' : 'flex flex-col gap-3'
                          }
                        >
                          {pinnedItems.map((item) => renderFeedItem(item, 'plan-pinned'))}
                        </div>
                      </TerrainCollapsibleFeedSection>
                    ) : null}

                    <div className="flex flex-col gap-2">
                      {planGroups.map((group) => (
                        <TerrainCollapsibleFeedSection
                          key={`plan-${group.section}`}
                          label={group.label}
                          count={sectionCountFor(group.section)}
                          dotVariant={group.dotVariant}
                          expanded={isExpanded(group.section)}
                          onToggle={() => toggle(group.section)}
                        >
                          <div
                            className={
                              isDesktopWeb
                                ? 'flex flex-col gap-1'
                                : 'flex flex-col gap-3'
                            }
                          >
                            {group.items.map((item) => renderFeedItem(item, 'plan'))}
                          </div>
                        </TerrainCollapsibleFeedSection>
                      ))}
                    </div>
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
                      {isFetchingMore ? 'Chargement…' : 'Afficher plus'}
                    </button>
                  </div>
                ) : null}
              </div>
            ) : null}
          </>
        )}
      </div>
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

  const isDesktopWeb = isDesktopWebLanding(useLgViewport())

  return (
    <div className="px-3 pb-2">
      <div
        className={cn(
          'flex flex-wrap items-center gap-2',
          isDesktopWeb && 'grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]',
        )}
      >
        <p className="min-w-0 flex-1 truncate text-sm font-semibold capitalize text-[#1a1a1a]">
          {periodLabel}
        </p>
        <div className={cn('order-3 w-full', isDesktopWeb && 'order-none w-auto justify-self-center')}>
          {granularityControl}
        </div>
        <div className={cn('ml-auto', isDesktopWeb && 'ml-0 justify-self-end')}>{nav}</div>
      </div>
    </div>
  )
}
