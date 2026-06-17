import { Plus } from 'lucide-react'
import { useMemo, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { canCreateChecklistTemplateFromBootstrapHints } from '@/features/auth/lib/bootstrap-permission-hints'
import { ChecklistTemplateSection } from '@/features/checklists/components/checklist-template-section'
import {
  useChecklistTemplatesQuery,
  useDeleteChecklistTemplateMutation,
} from '@/features/checklists/hooks'
import {
  getActiveExecutionIdFromDeleteError,
  resolveChecklistDeleteErrorMessage,
} from '@/features/checklists/lib/checklist-delete-flow'
import { canAccessChecklistLibrary } from '@/features/checklists/lib/checklist-management-access'
import type { ChecklistTemplateListFilters } from '@/features/checklists/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ChecklistHubPageProps = {
  onNavigate?: (pathname: string) => void
}

function filterButtonClass(isSelected: boolean): string {
  return cn(
    'rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
    isSelected
      ? 'bg-[#EEF2FF] text-[#1B4FD8]'
      : 'bg-[#F5F4F0] text-[#555] hover:bg-[#EBEAE4]',
  )
}

export function ChecklistHubPage({ onNavigate }: ChecklistHubPageProps) {
  const { navigate } = useAppRoute()
  const navigateTo = onNavigate ?? navigate
  const { activeMembership, bootstrap, isBootstrapping, isReady } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null
  const membershipId = activeMembership?.id ?? null
  const canAccessLibrary = canAccessChecklistLibrary({
    establishmentId,
    activeMembershipId: membershipId,
  })
  const canCreateTemplate = canCreateChecklistTemplateFromBootstrapHints(
    bootstrap?.permission_hints,
  )

  const [createdByMe, setCreatedByMe] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null)

  const filters = useMemo<ChecklistTemplateListFilters>(() => {
    const next: ChecklistTemplateListFilters = {}
    if (createdByMe) {
      next.created_by_me = true
    }
    return next
  }, [createdByMe])

  const templatesQuery = useChecklistTemplatesQuery(
    canAccessLibrary ? establishmentId : null,
    filters,
  )
  const deleteMutation = useDeleteChecklistTemplateMutation(establishmentId ?? '')

  if (!isReady || isBootstrapping) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!canAccessLibrary) {
    return (
      <div className="px-3 py-4">
        <TerrainCard>
          <p className={cn('text-sm', terrain.muted)}>
            Aucun établissement actif. Sélectionnez un établissement pour gérer vos checklists.
          </p>
        </TerrainCard>
      </div>
    )
  }

  if (templatesQuery.isError && templatesQuery.error && 'status' in templatesQuery.error) {
    const status = (templatesQuery.error as { status?: number }).status
    if (status === 403) {
      return (
        <div className="px-3 py-4">
          <TerrainCard>
            <p className={cn('text-sm', terrain.muted)}>
              Vous n&apos;avez pas accès à la bibliothèque de checklists.
            </p>
          </TerrainCard>
        </div>
      )
    }
  }

  async function handleDelete(templateId: string) {
    setDeleteError(null)
    setActiveExecutionId(null)
    try {
      await deleteMutation.mutateAsync(templateId)
    } catch (error) {
      setActiveExecutionId(getActiveExecutionIdFromDeleteError(error))
      setDeleteError(
        resolveChecklistDeleteErrorMessage(error, 'La checklist n’a pas pu être supprimée.'),
      )
    }
  }

  const createAction = canCreateTemplate ? (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="h-10 w-10 min-h-10 min-w-10 shrink-0 rounded-xl"
      aria-label="Créer une checklist"
      onClick={() => navigateTo('/checklists/new')}
    >
      <Plus className="h-5 w-5" />
    </Button>
  ) : null

  return (
    <div className="space-y-4 px-3 pb-24 pt-3">
      <div className="flex items-center justify-between gap-2">
        <p className={cn('text-sm', terrain.muted)}>Bibliothèque de checklists</p>
        {createAction}
      </div>

      <section className="space-y-2">
        <TerrainSectionLabel>Filtres</TerrainSectionLabel>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={filterButtonClass(createdByMe)}
            onClick={() => setCreatedByMe((current) => !current)}
          >
            Créées par moi
          </button>
        </div>
      </section>

      {deleteError ? (
        <TerrainCard className={terrain.errorSurface}>
          <p className="text-sm">{deleteError}</p>
          {activeExecutionId ? (
            <Button
              type="button"
              variant="outline"
              className="mt-3 h-10 w-full rounded-xl border-[#E8E6DF]"
              onClick={() => navigateTo(`/checklists/executions/${activeExecutionId}`)}
            >
              Ouvrir l&apos;exécution en cours
            </Button>
          ) : null}
        </TerrainCard>
      ) : null}

      <ChecklistTemplateSection
        templates={templatesQuery.data}
        isLoading={templatesQuery.isLoading}
        isError={templatesQuery.isError}
        emptyTitle="Aucune checklist"
        emptyDescription="Créez un modèle enregistré pour votre équipe."
        onOpenTemplate={(templateId) => navigateTo(`/checklists/${templateId}`)}
        onDeleteTemplate={(templateId) => void handleDelete(templateId)}
        deletingTemplateId={deleteMutation.isPending ? deleteMutation.variables : null}
      />
    </div>
  )
}
