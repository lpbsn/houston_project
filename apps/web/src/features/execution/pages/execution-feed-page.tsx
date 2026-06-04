import { useMemo, useState } from 'react'
import { LoaderCircle, Plus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { useSetTerrainHubHeaderAction } from '@/components/layout/terrain-hub-header-action'
import { Button } from '@/components/ui/button'
import { TerrainComingSoonState } from '@/components/layout/terrain-empty-state'
import { TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { ActionsApiError } from '@/features/actions/api'
import { useExecutionFeedQuery } from '@/features/actions/hooks'
import type { ExecutionViewMode } from '@/features/actions/types'

import { ExecutionCreateMenuSheet } from '../components/execution-create-menu-sheet'
import { ExecutionActionCard } from '../components/execution-action-card'
import { ExecutionFeedTabs } from '../components/execution-feed-tabs'
import { groupExecutionActionsBySection } from '../lib/execution-action-sections'

type ExecutionFeedPageProps = {
  onOpenAction?: (actionId: string) => void
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

function getEmptyFeedDescription(viewMode: ExecutionViewMode): string {
  if (viewMode === 'personal') {
    return 'Aucune action ne vous est assignée pour le moment.'
  }
  return 'Aucune action visible dans votre périmètre pour le moment.'
}

export function ExecutionFeedPage({ onOpenAction, onNavigate }: ExecutionFeedPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const [viewMode, setViewMode] = useState<ExecutionViewMode>('personal')
  const [isCreateMenuOpen, setIsCreateMenuOpen] = useState(false)

  const feedQuery = useExecutionFeedQuery(establishmentId, viewMode)

  const role = auth.bootstrap?.active_membership?.role
  const canCreate = role === 'owner' || role === 'director' || role === 'manager'

  const headerAction = useMemo(() => {
    if (!canCreate) {
      return null
    }

    return (
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-11 w-11 min-h-[44px] min-w-[44px] shrink-0 rounded-xl text-[#1a1a1a] hover:bg-[#F5F4F0]"
        aria-label="Créer"
        onClick={() => setIsCreateMenuOpen(true)}
      >
        <Plus className="h-5 w-5" />
      </Button>
    )
  }, [canCreate])

  useSetTerrainHubHeaderAction(headerAction)

  if (!establishmentId) {
    return (
      <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ExecutionCreateMenuSheet
        open={isCreateMenuOpen}
        onClose={() => setIsCreateMenuOpen(false)}
        onSelectAction={() => onNavigate?.('/actions/new')}
      />
      <div className="shrink-0 border-b border-[#E8E6DF] bg-white">
        <div className="px-3 pb-3 pt-1">
          <ExecutionFeedTabs viewMode={viewMode} onChange={setViewMode} />
        </div>
      </div>
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
        {feedQuery.isSuccess && feedQuery.data.items.length === 0 ? (
          <TerrainComingSoonState
            title="Aucune action"
            description={getEmptyFeedDescription(viewMode)}
          />
        ) : null}
        {feedQuery.isSuccess && feedQuery.data.items.length > 0 ? (
          <div className="flex flex-col gap-3 pt-5">
            {groupExecutionActionsBySection(
              feedQuery.data.items.flatMap((entry) =>
                entry.item_type === 'action' && entry.action ? [entry.action] : [],
              ),
            ).map((group) => (
              <section key={group.section}>
                <TerrainSectionLabel dotVariant={group.dotVariant} className="px-3">
                  {group.label} · {group.items.length}
                </TerrainSectionLabel>
                <div className="flex flex-col gap-3 px-3">
                  {group.items.map((item) => (
                    <ExecutionActionCard
                      key={item.id}
                      item={item}
                      onSelect={(id) => onOpenAction?.(id)}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}
