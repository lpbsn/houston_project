import { Ellipsis, Pencil, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { notifySuccess } from '@/lib/success-toast'
import { useLgViewport } from '@/lib/lg-viewport'

import {
  useActionPlanDetailQuery,
  useActivateActionPlanMutation,
  useDeactivateActionPlanMutation,
  useDeleteActionPlanMutation,
} from '../hooks'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import {
  canShowActionPlanActivate,
  canShowActionPlanDeactivate,
  canShowActionPlanDelete,
  canShowActionPlanUpdate,
} from '../lib/action-plan-permission-hints'

export const DELETE_TEMPLATE_CONFIRM =
  'Supprimer définitivement ce modèle ? Cette action est irréversible. Les actions planifiées seront supprimées.'

type ActionPlanTemplateDetailTopbarTrailingProps = {
  establishmentId: string
  actionPlanId: string
  onNavigate: (pathname: string) => void
}

export function ActionPlanTemplateDetailTopbarTrailing({
  establishmentId,
  actionPlanId,
  onNavigate,
}: ActionPlanTemplateDetailTopbarTrailingProps) {
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const detailQuery = useActionPlanDetailQuery(establishmentId, actionPlanId)
  const deleteMutation = useDeleteActionPlanMutation(establishmentId, actionPlanId)
  const activateMutation = useActivateActionPlanMutation(establishmentId, actionPlanId)
  const deactivateMutation = useDeactivateActionPlanMutation(establishmentId, actionPlanId)
  const [actionsOpen, setActionsOpen] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  if (detailQuery.isLoading || detailQuery.isError || !detailQuery.data) {
    return null
  }

  const hints = detailQuery.data.permission_hints
  const canUpdate = canShowActionPlanUpdate(hints)
  const canDelete = canShowActionPlanDelete(hints)
  const canActivate = canShowActionPlanActivate(hints)
  const canDeactivate = canShowActionPlanDeactivate(hints)

  async function handleDelete() {
    if (!window.confirm(DELETE_TEMPLATE_CONFIRM)) {
      return
    }
    try {
      await deleteMutation.mutateAsync()
      notifySuccess({ message: 'Modèle supprimé.', kind: 'deleted' })
      onNavigate('/action-plans')
    } catch {
      // Error feedback is shown on the detail page via shared mutation state.
    }
  }

  async function handleActivate() {
    setActionError(null)
    try {
      await activateMutation.mutateAsync()
      notifySuccess({ message: 'Modèle activé.', kind: 'activated' })
      setActionsOpen(false)
    } catch (error) {
      setActionError(resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être activé.'))
    }
  }

  async function handleDeactivate() {
    setActionError(null)
    try {
      await deactivateMutation.mutateAsync()
      notifySuccess({ message: 'Modèle désactivé.', kind: 'deactivated' })
      setActionsOpen(false)
    } catch (error) {
      setActionError(resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être désactivé.'))
    }
  }

  if (isDesktopWeb) {
    if (!canUpdate && !canDelete) {
      return null
    }

    return (
      <div className="flex w-auto items-center justify-end gap-2">
        {canUpdate ? (
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="h-10 w-10 shrink-0 rounded-full border-[#E8E6DF] bg-white text-[#1a1a1a] shadow-sm hover:bg-[#F5F4F0]"
            aria-label="Modifier"
            onClick={() => onNavigate(`/action-plans/${actionPlanId}/edit`)}
          >
            <Pencil className="h-4 w-4" aria-hidden />
          </Button>
        ) : null}
        {canDelete ? (
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="h-10 w-10 shrink-0 rounded-full border-[#E8E6DF] bg-white text-[#B42318] shadow-sm hover:bg-[#F5F4F0]"
            aria-label="Supprimer"
            disabled={deleteMutation.isPending}
            onClick={() => {
              void handleDelete()
            }}
          >
            <Trash2 className="h-4 w-4" aria-hidden />
          </Button>
        ) : null}
      </div>
    )
  }

  if (!canUpdate && !canActivate && !canDeactivate && !canDelete) {
    return null
  }

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="h-10 w-10 shrink-0 rounded-full border-[#E8E6DF] bg-white text-[#1a1a1a] shadow-sm hover:bg-[#F5F4F0]"
        aria-label="Actions du modèle"
        onClick={() => setActionsOpen(true)}
      >
        <Ellipsis className="h-4 w-4" aria-hidden />
      </Button>
      <TerrainBottomSheet
        title="Actions"
        open={actionsOpen}
        onClose={() => setActionsOpen(false)}
      >
        <div className="flex flex-col py-1">
          {actionError ? <p className="px-4 py-2 text-sm text-destructive">{actionError}</p> : null}
          {canUpdate ? (
            <Button
              type="button"
              variant="ghost"
              className="h-11 justify-start rounded-none px-4 text-sm"
              onClick={() => onNavigate(`/action-plans/${actionPlanId}/edit`)}
            >
              Modifier
            </Button>
          ) : null}
          {canActivate ? (
            <Button
              type="button"
              variant="ghost"
              className="h-11 justify-start rounded-none px-4 text-sm"
              disabled={activateMutation.isPending}
              onClick={() => void handleActivate()}
            >
              Activer
            </Button>
          ) : null}
          {canDeactivate ? (
            <Button
              type="button"
              variant="ghost"
              className="h-11 justify-start rounded-none px-4 text-sm text-[#E24B4A] hover:text-[#E24B4A]"
              disabled={deactivateMutation.isPending}
              onClick={() => void handleDeactivate()}
            >
              Désactiver
            </Button>
          ) : null}
          {canDelete ? (
            <Button
              type="button"
              variant="ghost"
              className="h-11 justify-start rounded-none px-4 text-sm text-[#B42318] hover:text-[#B42318]"
              disabled={deleteMutation.isPending}
              onClick={() => void handleDelete()}
            >
              Supprimer
            </Button>
          ) : null}
        </div>
      </TerrainBottomSheet>
    </>
  )
}
