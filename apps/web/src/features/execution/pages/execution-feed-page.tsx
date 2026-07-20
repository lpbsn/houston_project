import { useEffect, useState } from 'react'
import { LoaderCircle, Plus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { getBootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubViewToolbar } from '@/components/layout/terrain-hub-view-toolbar'
import { Button } from '@/components/ui/button'
import { TerrainEmptyState, TerrainErrorState, TerrainCollapsibleFeedSection } from '@/components/ui/terrain'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { useCollapsibleFeedSections } from '@/lib/use-collapsible-feed-sections'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'
import { ActionPlansApiError, unwrapActionPlanExecutionFeedItems } from '@/features/action-plans/api'
import { useActionPlanExecutionFeedQuery } from '@/features/action-plans/hooks'
import type { ActionPlanExecutionFeedResponse } from '@/features/action-plans/types'
import type { ExecutionViewMode } from '@/features/execution/lib/types'

import { ActionPlanExecutionFeedCard } from '../components/action-plan-execution-feed-card'
import { ExecutionCreateMenuSheet } from '../components/execution-create-menu-sheet'
import { ExecutionFeedTabs } from '../components/execution-feed-tabs'
import { ExecutionUpcomingNavRow } from '../components/execution-upcoming-nav-row'
import { ActionPlanExecutionFeedCardActionsSheet } from '@/features/action-plans/components/action-plan-execution-feed-card-actions-sheet'
import { useActionPlanExecutionFeedQuickActions } from '@/features/action-plans/hooks/use-action-plan-execution-feed-quick-actions'
import {
  groupActionPlanExecutionsBySection,
  mergeScheduledItemsIntoFeedSections,
  partitionActionPlanExecutionFeedPinnedItems,
} from '../lib/action-plan-execution-feed-sections'
import { canOpenExecutionCreateMenu } from '../lib/execution-create-menu'
import { getEmptyFeedDescription } from '../lib/execution-feed-empty'

const EXECUTION_FEED_DEFAULT_COLLAPSED_SECTIONS = ['done', 'canceled'] as const

type ExecutionFeedPageProps = {
  onOpenActionPlanExecution?: (executionId: string) => void
  onNavigate?: (pathname: string) => void
}

const PLANNING_FEEDBACK_STORAGE_KEY = 'houston:planning-feedback'

function readScheduledPreviewFromFeedPages(
  pages: ActionPlanExecutionFeedResponse[] | undefined,
): {
  scheduledItems: ReturnType<typeof unwrapActionPlanExecutionFeedItems>
  scheduledCount: number
} {
  if (!pages?.length) {
    return { scheduledItems: [], scheduledCount: 0 }
  }

  const pageWithScheduled =
    pages.find(
      (page) => page.scheduled_items != null || typeof page.scheduled_count === 'number',
    ) ?? pages[0]

  return {
    scheduledItems: unwrapActionPlanExecutionFeedItems(pageWithScheduled?.scheduled_items ?? []),
    scheduledCount: pageWithScheduled?.scheduled_count ?? 0,
  }
}

export function ExecutionFeedPage({
  onOpenActionPlanExecution,
  onNavigate,
}: ExecutionFeedPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const [viewMode, setViewMode] = useState<ExecutionViewMode>('personal')
  const [isCreateMenuOpen, setIsCreateMenuOpen] = useState(false)
  const [planningFeedback, setPlanningFeedback] = useState<string | null>(null)

  useEffect(() => {
    const message = sessionStorage.getItem(PLANNING_FEEDBACK_STORAGE_KEY)
    if (!message) {
      return
    }
    sessionStorage.removeItem(PLANNING_FEEDBACK_STORAGE_KEY)
    setPlanningFeedback(message)
  }, [])

  const planFeedQuery = useActionPlanExecutionFeedQuery(establishmentId, viewMode)
  const quickActions = useActionPlanExecutionFeedQuickActions({
    establishmentId,
    viewMode,
  })

  const planItems = planFeedQuery.isSuccess
    ? unwrapActionPlanExecutionFeedItems(planFeedQuery.data.pages.flatMap((page) => page.items))
    : []
  const { scheduledItems, scheduledCount } = planFeedQuery.isSuccess
    ? readScheduledPreviewFromFeedPages(planFeedQuery.data.pages)
    : { scheduledItems: [], scheduledCount: 0 }
  const { pinnedItems, unpinnedItems } = partitionActionPlanExecutionFeedPinnedItems(planItems)
  const planGroups = mergeScheduledItemsIntoFeedSections(
    groupActionPlanExecutionsBySection(unpinnedItems),
    scheduledItems,
  )
  const sectionKeys = planGroups.map((group) => group.section)
  const { isExpanded, toggle } = useCollapsibleFeedSections(sectionKeys, {
    defaultCollapsedKeys: EXECUTION_FEED_DEFAULT_COLLAPSED_SECTIONS,
    resetToken: viewMode,
  })

  const permissionHints = auth.bootstrap
    ? getBootstrapPermissionHints(auth.bootstrap)
    : null
  const canCreate =
    auth.bootstrap != null &&
    !auth.isBootstrapping &&
    canOpenExecutionCreateMenu(permissionHints)

  const isInitialLoading = planFeedQuery.isLoading
  const showGlobalEmpty =
    planItems.length === 0 &&
    scheduledItems.length === 0 &&
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

  if (!establishmentId) {
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
      <TerrainHubSubheader>
        <TerrainHubViewToolbar trailing={createAction}>
          <ExecutionFeedTabs viewMode={viewMode} onChange={setViewMode} />
        </TerrainHubViewToolbar>
      </TerrainHubSubheader>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-3 pb-4">
        {planningFeedback ? (
          <div className="pt-3">
            <TerrainFeedback variant="success" message={planningFeedback} />
          </div>
        ) : null}
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

            {planFeedQuery.isSuccess && onNavigate ? (
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
                        onSelect={(id) => onOpenActionPlanExecution?.(id)}
                        onOpenActions={quickActions.openActions}
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
                              onSelect={(id) => onOpenActionPlanExecution?.(id)}
                              onOpenActions={quickActions.openActions}
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
                description={getEmptyFeedDescription(viewMode)}
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
