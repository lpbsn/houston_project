import { useState } from 'react'
import { LoaderCircle, Plus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { getBootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubViewToolbar } from '@/components/layout/terrain-hub-view-toolbar'
import { Button } from '@/components/ui/button'
import { TerrainEmptyState, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { ActionsApiError } from '@/features/actions/api'
import { useExecutionFeedQuery } from '@/features/actions/hooks'
import type { ExecutionViewMode } from '@/features/actions/types'
import { ActionPlansApiError, unwrapActionPlanExecutionFeedItems } from '@/features/action-plans/api'
import { useActionPlanExecutionFeedQuery } from '@/features/action-plans/hooks'

import { ActionPlanExecutionFeedCard } from '../components/action-plan-execution-feed-card'
import { ExecutionCreateMenuSheet } from '../components/execution-create-menu-sheet'
import { ExecutionActionCard } from '../components/execution-action-card'
import { ExecutionChecklistCard } from '../components/execution-checklist-card'
import { ExecutionFeedTabs } from '../components/execution-feed-tabs'
import { groupActionPlanExecutionsBySection } from '../lib/action-plan-execution-feed-sections'
import { groupExecutionActionsBySection } from '../lib/execution-action-sections'
import { canOpenExecutionCreateMenu } from '../lib/execution-create-menu'
import { getEmptyFeedDescription } from '../lib/execution-feed-empty'
import { splitExecutionFeedItems } from '../lib/execution-feed-sections'

type ExecutionFeedPageProps = {
  onOpenAction?: (actionId: string) => void
  onOpenChecklist?: (executionId: string) => void
  onOpenActionPlanExecution?: (executionId: string) => void
  onNavigate?: (pathname: string) => void
}

export function ExecutionFeedPage({
  onOpenAction,
  onOpenChecklist,
  onOpenActionPlanExecution,
  onNavigate,
}: ExecutionFeedPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const [viewMode, setViewMode] = useState<ExecutionViewMode>('personal')
  const [isCreateMenuOpen, setIsCreateMenuOpen] = useState(false)

  const planFeedQuery = useActionPlanExecutionFeedQuery(establishmentId, viewMode)
  const legacyFeedQuery = useExecutionFeedQuery(establishmentId, viewMode)

  const planItems = planFeedQuery.isSuccess
    ? unwrapActionPlanExecutionFeedItems(planFeedQuery.data.pages.flatMap((page) => page.items))
    : []
  const planGroups = groupActionPlanExecutionsBySection(planItems)

  const legacyFeedItems = legacyFeedQuery.isSuccess
    ? legacyFeedQuery.data.pages.flatMap((page) => page.items)
    : []
  const { checklistItems, actionItems } = splitExecutionFeedItems(legacyFeedItems)
  const actionGroups = groupExecutionActionsBySection(actionItems)

  const permissionHints = auth.bootstrap
    ? getBootstrapPermissionHints(auth.bootstrap)
    : null
  const canCreate =
    auth.bootstrap != null &&
    !auth.isBootstrapping &&
    canOpenExecutionCreateMenu(permissionHints)

  const isInitialLoading = planFeedQuery.isLoading && legacyFeedQuery.isLoading
  const hasAnyContent =
    planItems.length > 0 || checklistItems.length > 0 || actionItems.length > 0
  const showGlobalEmpty =
    !hasAnyContent &&
    planFeedQuery.isSuccess &&
    legacyFeedQuery.isSuccess &&
    !planFeedQuery.isLoading &&
    !legacyFeedQuery.isLoading
  const hasMore = planFeedQuery.hasNextPage || legacyFeedQuery.hasNextPage
  const isFetchingMore = planFeedQuery.isFetchingNextPage || legacyFeedQuery.isFetchingNextPage

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
        onSelectAction={() => onNavigate?.('/actions/new')}
        onSelectChecklistCreate={() => onNavigate?.('/checklists/new')}
        onSelectChecklistUse={() => onNavigate?.('/checklists')}
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

            {legacyFeedQuery.isError ? (
              <TerrainErrorState
                message={resolveApiErrorMessage(
                  legacyFeedQuery.error,
                  ActionsApiError,
                  'Une erreur est survenue.',
                )}
                onRetry={() => void legacyFeedQuery.refetch()}
              />
            ) : null}

            {legacyFeedQuery.isSuccess ? (
              <>
                {checklistItems.length > 0 ? (
                  <div className="flex flex-col gap-3">
                    {checklistItems.map((item) => (
                      <ExecutionChecklistCard
                        key={`checklist-${item.id}`}
                        item={item}
                        onSelect={(id) => onOpenChecklist?.(id)}
                      />
                    ))}
                  </div>
                ) : null}
                {actionGroups.map((group) => (
                  <section key={group.section}>
                    <TerrainSectionLabel dotVariant={group.dotVariant} className="px-3">
                      {group.label} · {group.items.length}
                    </TerrainSectionLabel>
                    <div className="flex flex-col gap-3">
                      {group.items.map((action) => (
                        <ExecutionActionCard
                          key={`action-${action.id}`}
                          item={action}
                          onSelect={(id) => onOpenAction?.(id)}
                        />
                      ))}
                    </div>
                  </section>
                ))}
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
                  onClick={() => {
                    if (planFeedQuery.hasNextPage) {
                      void planFeedQuery.fetchNextPage()
                    }
                    if (legacyFeedQuery.hasNextPage) {
                      void legacyFeedQuery.fetchNextPage()
                    }
                  }}
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
