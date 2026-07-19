import { useState } from 'react'
import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubViewToolbar } from '@/components/layout/terrain-hub-view-toolbar'
import { TerrainEmptyState, TerrainErrorState } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { ActionPlansApiError, unwrapActionPlanExecutionFeedItems } from '@/features/action-plans/api'
import { useActionPlanExecutionUpcomingQuery } from '@/features/action-plans/hooks'
import { ActionPlanExecutionFeedCardActionsSheet } from '@/features/action-plans/components/action-plan-execution-feed-card-actions-sheet'
import { useActionPlanExecutionFeedQuickActions } from '@/features/action-plans/hooks/use-action-plan-execution-feed-quick-actions'
import type { ExecutionViewMode } from '@/features/execution/lib/types'

import { ActionPlanExecutionFeedCard } from '../components/action-plan-execution-feed-card'
import { ExecutionFeedTabs } from '../components/execution-feed-tabs'

type ExecutionUpcomingPageProps = {
  onOpenActionPlanExecution?: (executionId: string) => void
}

export function ExecutionUpcomingPage({
  onOpenActionPlanExecution,
}: ExecutionUpcomingPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const [viewMode, setViewMode] = useState<ExecutionViewMode>('personal')

  const upcomingQuery = useActionPlanExecutionUpcomingQuery(establishmentId, viewMode)
  const quickActions = useActionPlanExecutionFeedQuickActions({
    establishmentId,
    viewMode,
  })

  const items = upcomingQuery.isSuccess
    ? unwrapActionPlanExecutionFeedItems(upcomingQuery.data.pages.flatMap((page) => page.items))
    : []

  const isInitialLoading = upcomingQuery.isLoading
  const showEmpty = items.length === 0 && upcomingQuery.isSuccess && !upcomingQuery.isLoading
  const hasMore = upcomingQuery.hasNextPage
  const isFetchingMore = upcomingQuery.isFetchingNextPage

  if (!establishmentId) {
    return (
      <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <TerrainHubSubheader className="border-b-0">
        <TerrainHubViewToolbar>
          <ExecutionFeedTabs viewMode={viewMode} onChange={setViewMode} />
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

            {upcomingQuery.isSuccess && items.length > 0 ? (
              <div className="flex flex-col gap-3">
                {items.map((item) => (
                  <ActionPlanExecutionFeedCard
                    key={`upcoming-${item.id}`}
                    item={item}
                    onSelect={(id) => onOpenActionPlanExecution?.(id)}
                    onOpenActions={quickActions.openActions}
                  />
                ))}
              </div>
            ) : null}

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
