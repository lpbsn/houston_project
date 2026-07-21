import { Pencil, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'

import { useActionPlanDetailQuery, useDeleteActionPlanMutation } from '../hooks'
import {
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
  const detailQuery = useActionPlanDetailQuery(establishmentId, actionPlanId)
  const deleteMutation = useDeleteActionPlanMutation(establishmentId, actionPlanId)

  if (detailQuery.isLoading || detailQuery.isError || !detailQuery.data) {
    return null
  }

  const canUpdate = canShowActionPlanUpdate(detailQuery.data.permission_hints)
  const canDelete = canShowActionPlanDelete(detailQuery.data.permission_hints)

  if (!canUpdate && !canDelete) {
    return null
  }

  async function handleDelete() {
    if (!window.confirm(DELETE_TEMPLATE_CONFIRM)) {
      return
    }
    try {
      await deleteMutation.mutateAsync()
      onNavigate('/action-plans')
    } catch {
      // Error feedback is shown on the detail page via shared mutation state.
    }
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
