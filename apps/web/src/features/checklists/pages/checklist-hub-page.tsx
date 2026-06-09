import { LoaderCircle, Plus } from 'lucide-react'
import { useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainSectionLabel } from '@/components/layout/terrain-card'
import { Button } from '@/components/ui/button'
import type { RoleEnum } from '@/features/auth/types'
import { ChecklistCreateMenuSheet } from '@/features/checklists/components/checklist-create-menu-sheet'
import { ChecklistTemplateSection } from '@/features/checklists/components/checklist-template-section'
import {
  useChecklistTemplatesQuery,
  useDeleteChecklistTemplateMutation,
} from '@/features/checklists/hooks'
import {
  getActiveExecutionIdFromDeleteError,
  resolveChecklistDeleteErrorMessage,
} from '@/features/checklists/lib/checklist-delete-flow'
import {
  canSeePersonalChecklistManagement,
  canSeeSharedChecklistManagement,
} from '@/features/checklists/lib/checklist-management-access'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const INVITATION_ROLES: RoleEnum[] = ['owner', 'director', 'manager', 'staff']

type ChecklistHubPageProps = {
  onNavigate?: (pathname: string) => void
}

function toRoleEnum(role: string | null | undefined): RoleEnum | null {
  if (!role) {
    return null
  }

  return INVITATION_ROLES.find((candidate) => candidate === role) ?? null
}

export function ChecklistHubPage({ onNavigate }: ChecklistHubPageProps) {
  const { navigate } = useAppRoute()
  const navigateTo = onNavigate ?? navigate
  const { activeMembership, isBootstrapping, isReady } = useAuth()
  const role = toRoleEnum(activeMembership?.role)
  const establishmentId = activeMembership?.establishment_id ?? null
  const canSeeShared = canSeeSharedChecklistManagement(role)
  const canSeePersonal = canSeePersonalChecklistManagement(role)

  const [isCreateMenuOpen, setIsCreateMenuOpen] = useState(false)
  const [sharedDeleteError, setSharedDeleteError] = useState<string | null>(null)
  const [sharedActiveExecutionId, setSharedActiveExecutionId] = useState<string | null>(null)
  const [personalDeleteError, setPersonalDeleteError] = useState<string | null>(null)
  const [personalActiveExecutionId, setPersonalActiveExecutionId] = useState<string | null>(null)

  const sharedQuery = useChecklistTemplatesQuery(
    canSeeShared ? establishmentId : null,
    'shared',
  )
  const personalQuery = useChecklistTemplatesQuery(
    canSeePersonal ? establishmentId : null,
    'personal',
  )

  const deleteSharedMutation = useDeleteChecklistTemplateMutation(establishmentId ?? '', 'shared')
  const deletePersonalMutation = useDeleteChecklistTemplateMutation(
    establishmentId ?? '',
    'personal',
  )

  if (!isReady || isBootstrapping) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!activeMembership || !role || !establishmentId) {
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

  async function handleDeleteShared(templateId: string) {
    setSharedDeleteError(null)
    setSharedActiveExecutionId(null)
    try {
      await deleteSharedMutation.mutateAsync(templateId)
    } catch (error) {
      setSharedActiveExecutionId(getActiveExecutionIdFromDeleteError(error))
      setSharedDeleteError(
        resolveChecklistDeleteErrorMessage(error, 'La checklist n’a pas pu être supprimée.'),
      )
    }
  }

  async function handleDeletePersonal(templateId: string) {
    setPersonalDeleteError(null)
    setPersonalActiveExecutionId(null)
    try {
      await deletePersonalMutation.mutateAsync(templateId)
    } catch (error) {
      setPersonalActiveExecutionId(getActiveExecutionIdFromDeleteError(error))
      setPersonalDeleteError(
        resolveChecklistDeleteErrorMessage(error, 'La checklist n’a pas pu être supprimée.'),
      )
    }
  }

  const createAction = (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="h-10 w-10 min-h-10 min-w-10 shrink-0 rounded-xl"
      aria-label="Créer une checklist"
      onClick={() => setIsCreateMenuOpen(true)}
    >
      <Plus className="h-5 w-5" />
    </Button>
  )

  return (
    <div className="space-y-4 px-3 pb-24 pt-3">
      <ChecklistCreateMenuSheet
        open={isCreateMenuOpen}
        role={role}
        onClose={() => setIsCreateMenuOpen(false)}
        onSelectShared={() => navigateTo('/checklists/shared/new')}
        onSelectPersonal={() => navigateTo('/checklists/personal/new')}
      />

      <div className="flex items-center justify-between gap-2">
        <p className={cn('text-sm', terrain.muted)}>Vos modèles de checklists</p>
        {createAction}
      </div>

      {canSeeShared ? (
        <section className="space-y-2">
          <TerrainSectionLabel>Checklists partagées</TerrainSectionLabel>
          {sharedDeleteError ? (
            <TerrainCard className={terrain.errorSurface}>
              <p className="text-sm">{sharedDeleteError}</p>
              {sharedActiveExecutionId ? (
                <Button
                  type="button"
                  variant="outline"
                  className="mt-3 h-10 w-full rounded-xl border-[#E8E6DF]"
                  onClick={() => navigateTo(`/checklists/executions/${sharedActiveExecutionId}`)}
                >
                  Ouvrir l&apos;exécution en cours
                </Button>
              ) : null}
            </TerrainCard>
          ) : null}
          <ChecklistTemplateSection
            templates={sharedQuery.data}
            isLoading={sharedQuery.isLoading}
            isError={sharedQuery.isError}
            emptyTitle="Aucune checklist partagée"
            emptyDescription="Créez un modèle partagé pour votre équipe."
            onOpenTemplate={(templateId) => navigateTo(`/checklists/shared/${templateId}`)}
            onDeleteTemplate={(templateId) => void handleDeleteShared(templateId)}
            deletingTemplateId={
              deleteSharedMutation.isPending ? deleteSharedMutation.variables : null
            }
          />
        </section>
      ) : null}

      {canSeePersonal ? (
        <section className="space-y-2">
          <TerrainSectionLabel>
            {canSeeShared ? 'Checklists personnelles' : 'Mes checklists'}
          </TerrainSectionLabel>
          {personalDeleteError ? (
            <TerrainCard className={terrain.errorSurface}>
              <p className="text-sm">{personalDeleteError}</p>
              {personalActiveExecutionId ? (
                <Button
                  type="button"
                  variant="outline"
                  className="mt-3 h-10 w-full rounded-xl border-[#E8E6DF]"
                  onClick={() => navigateTo(`/checklists/executions/${personalActiveExecutionId}`)}
                >
                  Ouvrir l&apos;exécution en cours
                </Button>
              ) : null}
            </TerrainCard>
          ) : null}
          <ChecklistTemplateSection
            templates={personalQuery.data}
            isLoading={personalQuery.isLoading}
            isError={personalQuery.isError}
            emptyTitle="Aucune checklist personnelle"
            emptyDescription="Créez une routine personnelle pour structurer votre exécution."
            onOpenTemplate={(templateId) => navigateTo(`/checklists/personal/${templateId}`)}
            onDeleteTemplate={(templateId) => void handleDeletePersonal(templateId)}
            deletingTemplateId={
              deletePersonalMutation.isPending ? deletePersonalMutation.variables : null
            }
          />
        </section>
      ) : null}

      {(sharedQuery.isLoading || personalQuery.isLoading) &&
      !sharedQuery.data?.length &&
      !personalQuery.data?.length ? (
        <div className="flex items-center justify-center gap-2 py-8 text-sm text-[#7D7B75]">
          <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
          Chargement des checklists...
        </div>
      ) : null}
    </div>
  )
}
