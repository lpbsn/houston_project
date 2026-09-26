import { useState } from 'react'
import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubViewToolbar } from '@/components/layout/terrain-hub-view-toolbar'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { TerrainEmptyState, TerrainErrorState } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { useLgViewport } from '@/lib/lg-viewport'
import { ActionPlansApiError, unwrapActionPlanExecutionFeedItems } from '@/features/action-plans/api'
import { useActionPlanExecutionUpcomingQuery } from '@/features/action-plans/hooks'
import { ActionPlanExecutionFeedCardActionsSheet } from '@/features/action-plans/components/action-plan-execution-feed-card-actions-sheet'
import { useActionPlanExecutionFeedQuickActions } from '@/features/action-plans/hooks/use-action-plan-execution-feed-quick-actions'
import type { ExecutionViewMode } from '@/features/execution/lib/types'

import { ActionPlanExecutionFeedCard } from '../components/action-plan-execution-feed-card'
import { ActionPlanExecutionFeedDesktopRow } from '../components/action-plan-execution-feed-desktop-row'
import { ExecutionFeedTabs } from '../components/execution-feed-tabs'
import { groupScheduledItemsByStartDate } from '../lib/action-plan-execution-feed-card-display'

type ExecutionUpcomingPageProps = {
  onOpenActionPlanExecution?: (executionId: string) => void
  source?: 'establishment' | 'cross'
}

export function ExecutionUpcomingPage({
  onOpenActionPlanExecution,
  source = 'establishment',
}: ExecutionUpcomingPageProps) {
  const auth = useAuth()
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const isCross = source === 'cross'
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const [viewMode, setViewMode] = useState<ExecutionViewMode>('personal')

  const upcomingQuery = useActionPlanExecutionUpcomingQuery(establishmentId, viewMode, {
    source,
  })
  const quickActions = useActionPlanExecutionFeedQuickActions({
    establishmentId,
    viewMode,
  })

  const items = upcomingQuery.isSuccess
    ? unwrapActionPlanExecutionFeedItems(upcomingQuery.data.pages.flatMap((page) => page.items))
    : []
  const groups = groupScheduledItemsByStartDate(items)

  const isInitialLoading = upcomingQuery.isLoading
  const showEmpty = items.length === 0 && upcomingQuery.isSuccess && !upcomingQuery.isLoading
  const hasMore = upcomingQuery.hasNextPage
  const isFetchingMore = upcomingQuery.isFetchingNextPage

  if (!establishmentId && !isCross) {
    return (
      <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <TerrainHubSubheader>
        <TerrainHubViewToolbar>
          <ExecutionFeedTabs
            viewMode={viewMode}
            onChange={setViewMode}
            size={isDesktopWeb ? 'default' : 'compact'}
          />
        </TerrainHubViewToolbar>
      </TerrainHubSubheader>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-3 pb-4">
        {isInitialLoading ? (
          <div className="flex items-center justify-center py-16 text-[#7D7B75]">
            <LoaderCircle className="h-6 w-6 animate-spin" />
          </div>
        ) : null}

        {!isInitialLoading ? (
          <div className="flex flex-col gap-3 pt-5">
            {!isCross && quickActions.actionError ? (
              <TerrainFeedback variant="error" message={quickActions.actionError} />
            ) : null}

            {upcomingQuery.isError ? (
              <TerrainErrorState
                message={resolveApiErrorMessage(
                  upcomingQuery.error,
                  ActionPlansApiError,
                  'Impossible de charger les plans à venir.',
                )}
                onRetry={() => void upcomingQuery.refetch()}
              />
            ) : null}

            {groups.map((group) => (
              <div key={group.key} className="flex flex-col gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-[#7D7B75]">
                  {group.label}
                </p>
                <div
                  className={isDesktopWeb ? 'flex flex-col gap-1' : 'flex flex-col gap-3'}
                >
                  {group.items.map((item) =>
                    isDesktopWeb ? (
                      <ActionPlanExecutionFeedDesktopRow
                        key={`upcoming-${item.id}`}
                        item={item}
                        onSelect={(id) => onOpenActionPlanExecution?.(id)}
                        onTogglePin={
                          isCross
                            ? undefined
                            : (feedItem) => {
                                quickActions.clearActionError()
                                quickActions.runAction('pin', feedItem)
                              }
                        }
                      />
                    ) : (
                      <ActionPlanExecutionFeedCard
                        key={`upcoming-${item.id}`}
                        item={item}
                        onSelect={(id) => onOpenActionPlanExecution?.(id)}
                        onTogglePin={
                          isCross
                            ? undefined
                            : (feedItem) => {
                                quickActions.clearActionError()
                                quickActions.runAction('pin', feedItem)
                              }
                        }
                      />
                    ),
                  )}
                </div>
              </div>
            ))}

            {showEmpty ? (
              <TerrainEmptyState
                className="mx-3 mt-3"
                title="Aucune planification"
                description="Aucun plan d’action programmé à venir."
              />
            ) : null}

            {hasMore ? (
              <div className="flex justify-center py-4">
                <button
                  type="button"
                  className="text-xs font-semibold text-[#1B4FD8] disabled:opacity-60"
                  onClick={() => void upcomingQuery.fetchNextPage()}
                  disabled={isFetchingMore}
                >
                  {isFetchingMore ? 'Chargement…' : 'Afficher plus'}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {!isDesktopWeb && !isCross && quickActions.activeItem ? (
        <ActionPlanExecutionFeedCardActionsSheet
          open={quickActions.actionsOpen}
          item={quickActions.activeItem}
          isPending={quickActions.isPending}
          onClose={quickActions.closeActions}
          onSelectAction={(actionId) => quickActions.runAction(actionId)}
        />
      ) : null}
    </div>
  )
}
