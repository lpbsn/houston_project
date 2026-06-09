import { useState } from 'react'
import { LoaderCircle, Plus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubViewToolbar } from '@/components/layout/terrain-hub-view-toolbar'
import { Button } from '@/components/ui/button'
import { TerrainEmptyState, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { ActionsApiError } from '@/features/actions/api'
import { useExecutionFeedQuery } from '@/features/actions/hooks'
import type { ExecutionViewMode } from '@/features/actions/types'

import { ExecutionCreateMenuSheet } from '../components/execution-create-menu-sheet'
import { ExecutionActionCard } from '../components/execution-action-card'
import { ExecutionChecklistCard } from '../components/execution-checklist-card'
import { ExecutionFeedTabs } from '../components/execution-feed-tabs'
import { groupExecutionActionsBySection } from '../lib/execution-action-sections'
import { canOpenExecutionCreateMenu } from '../lib/execution-create-menu'
import { getEmptyFeedDescription } from '../lib/execution-feed-empty'
import { splitExecutionFeedItems } from '../lib/execution-feed-sections'

type ExecutionFeedPageProps = {
  onOpenAction?: (actionId: string) => void
  onOpenChecklist?: (executionId: string) => void
  onNavigate?: (pathname: string) => void
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ActionsApiError) {
    return error.detail
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Une erreur est survenue.'
}

export function ExecutionFeedPage({
  onOpenAction,
  onOpenChecklist,
  onNavigate,
}: ExecutionFeedPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const [viewMode, setViewMode] = useState<ExecutionViewMode>('personal')
  const [isCreateMenuOpen, setIsCreateMenuOpen] = useState(false)

  const feedQuery = useExecutionFeedQuery(establishmentId, viewMode)
  const feedItems = feedQuery.isSuccess ? feedQuery.data.items : []
  const { checklistItems, actionItems } = splitExecutionFeedItems(feedItems)
  const actionGroups = groupExecutionActionsBySection(actionItems)

  const role = auth.bootstrap?.active_membership?.role
  const canCreate = canOpenExecutionCreateMenu(role)

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
        role={role}
        onClose={() => setIsCreateMenuOpen(false)}
        onSelectAction={() => onNavigate?.('/actions/new')}
        onSelectFlashTodo={() => onNavigate?.('/checklists/executions/new')}
        onSelectChecklistCreate={() => onNavigate?.('/checklists/new')}
        onSelectChecklistUse={() => onNavigate?.('/checklists')}
      />
      <TerrainHubSubheader>
        <TerrainHubViewToolbar trailing={createAction}>
          <ExecutionFeedTabs viewMode={viewMode} onChange={setViewMode} />
        </TerrainHubViewToolbar>
      </TerrainHubSubheader>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-3 pb-4">
        {feedQuery.isLoading ? (
          <div className="flex items-center justify-center py-16 text-[#7D7B75]">
            <LoaderCircle className="h-6 w-6 animate-spin" />
          </div>
        ) : null}
        {feedQuery.isError ? (
          <TerrainErrorState
            message={getErrorMessage(feedQuery.error)}
            onRetry={() => void feedQuery.refetch()}
          />
        ) : null}
        {feedQuery.isSuccess ? (
          <div className="flex flex-col gap-3 pt-5">
            {feedQuery.data.items.length === 0 ? (
              <TerrainEmptyState
                className="mx-3 mt-3"
                title="Aucune exécution"
                description={getEmptyFeedDescription(viewMode)}
              />
            ) : (
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
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}
