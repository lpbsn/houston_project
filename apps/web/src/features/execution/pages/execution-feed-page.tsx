import { useState } from 'react'
import { LoaderCircle, Plus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { getBootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubViewToolbar } from '@/components/layout/terrain-hub-view-toolbar'
import { Button } from '@/components/ui/button'
import { TerrainEmptyState, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { ActionPlansApiError, unwrapActionPlanExecutionFeedItems } from '@/features/action-plans/api'
import { useActionPlanExecutionFeedQuery } from '@/features/action-plans/hooks'
import type { ExecutionViewMode } from '@/features/execution/lib/types'

import { ActionPlanExecutionFeedCard } from '../components/action-plan-execution-feed-card'
import { ExecutionCreateMenuSheet } from '../components/execution-create-menu-sheet'
import { ExecutionFeedTabs } from '../components/execution-feed-tabs'
import { groupActionPlanExecutionsBySection } from '../lib/action-plan-execution-feed-sections'
import { canOpenExecutionCreateMenu } from '../lib/execution-create-menu'
import { getEmptyFeedDescription } from '../lib/execution-feed-empty'

type ExecutionFeedPageProps = {
  onOpenActionPlanExecution?: (executionId: string) => void
  onNavigate?: (pathname: string) => void
}

export function ExecutionFeedPage({
  onOpenActionPlanExecution,
  onNavigate,
}: ExecutionFeedPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const [viewMode, setViewMode] = useState<ExecutionViewMode>('personal')
  const [isCreateMenuOpen, setIsCreateMenuOpen] = useState(false)

  const planFeedQuery = useActionPlanExecutionFeedQuery(establishmentId, viewMode)

  const planItems = planFeedQuery.isSuccess
    ? unwrapActionPlanExecutionFeedItems(planFeedQuery.data.pages.flatMap((page) => page.items))
    : []
  const planGroups = groupActionPlanExecutionsBySection(planItems)

  const permissionHints = auth.bootstrap
    ? getBootstrapPermissionHints(auth.bootstrap)
    : null
  const canCreate =
    auth.bootstrap != null &&
    !auth.isBootstrapping &&
    canOpenExecutionCreateMenu(permissionHints)

  const isInitialLoading = planFeedQuery.isLoading
  const showGlobalEmpty =
    planItems.length === 0 && planFeedQuery.isSuccess && !planFeedQuery.isLoading
  const hasMore = planFeedQuery.hasNextPage
  const isFetchingMore = planFeedQuery.isFetchingNextPage

  const createAction = canCreate ? (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="h-10 w-10 min-h-10 min-w-10 shrink-0 rounded-xl"
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
        onSelectActionPlan={() => onNavigate?.('/execution/plans/new')}
        onSelectCatalog={() => onNavigate?.('/action-plans')}
      />
      <TerrainHubSubheader>
        <TerrainHubViewToolbar trailing={createAction}>
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

            {planFeedQuery.isSuccess && planGroups.length > 0
              ? planGroups.map((group) => (
                  <section key={`plan-${group.section}`}>
                    <TerrainSectionLabel dotVariant={group.dotVariant} className="px-3">
                      {group.label} · {group.items.length}
                    </TerrainSectionLabel>
                    <div className="flex flex-col gap-3">
                      {group.items.map((item) => (
                        <ActionPlanExecutionFeedCard
                          key={`plan-${item.id}`}
                          item={item}
                          onSelect={(id) => onOpenActionPlanExecution?.(id)}
                        />
                      ))}
                    </div>
                  </section>
                ))
              : null}

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
    </div>
  )
}
