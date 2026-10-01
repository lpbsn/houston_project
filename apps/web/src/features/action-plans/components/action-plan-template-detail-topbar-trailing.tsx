import { Ban, MoreHorizontal, Pencil, Power, Trash2, type LucideIcon } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { notifySuccess } from '@/lib/success-toast'
import { terrain } from '@/lib/terrain-styles'
import { useLgViewport } from '@/lib/lg-viewport'
import { cn } from '@/lib/utils'

import {
  useActionPlanDetailQuery,
  useActivateActionPlanMutation,
  useDeactivateActionPlanMutation,
  useDeleteActionPlanMutation,
} from '../hooks'
import { formatCatalogStatusLabel } from '../lib/action-plan-display'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import {
  canShowActionPlanActivate,
  canShowActionPlanDeactivate,
  canShowActionPlanDelete,
  canShowActionPlanUpdate,
} from '../lib/action-plan-permission-hints'

export const DELETE_TEMPLATE_CONFIRM =
  'Supprimer définitivement ce modèle ? Cette action est irréversible. Les actions planifiées seront supprimées.'

function MobileActionRow({
  icon: Icon,
  label,
  tone,
  disabled,
  onClick,
}: {
  icon: LucideIcon
  label: string
  tone: 'neutral' | 'danger'
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <li>
      <button
        type="button"
        className={cn(
          'flex min-h-[52px] w-full items-center gap-3 rounded-lg border px-3 py-3 text-left transition active:scale-[0.99] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
          tone === 'danger'
            ? cn(terrain.errorSurface, terrain.danger)
            : 'border-[#E8E6DF] bg-[#F5F4F0] text-[#1a1a1a]',
        )}
        disabled={disabled}
        onClick={onClick}
      >
        <Icon className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
        <span
          className={cn(
            'text-[15px] font-semibold',
            tone === 'danger' ? terrain.danger : 'text-[#1a1a1a]',
          )}
        >
          {label}
        </span>
      </button>
    </li>
  )
}

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
    } catch (error) {
      setActionError(
        resolveActionPlanErrorMessage(error, 'Le modèle n’a pas pu être supprimé.'),
      )
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

  const catalogStatusLabel =
    detailQuery.data.catalog_status === 'active' || detailQuery.data.catalog_status === 'inactive'
      ? formatCatalogStatusLabel(detailQuery.data.catalog_status)
      : null

  return (
    <>
      <button
        type="button"
        className="inline-flex h-10 w-10 items-center justify-center rounded-full text-[#5F5A52]"
        aria-label="Actions du modèle"
        aria-haspopup="dialog"
        onClick={() => {
          setActionError(null)
          setActionsOpen(true)
        }}
      >
        <MoreHorizontal className="h-5 w-5" aria-hidden />
      </button>
      <TerrainBottomSheet
        title="Actions"
        open={actionsOpen}
        onClose={() => setActionsOpen(false)}
      >
        <div className="mb-3 rounded-xl border border-[#E8E6DF] bg-[#F9F8F5] px-3 py-2.5">
          {catalogStatusLabel ? (
            <p className="mb-1 text-[11px] text-[#888]">{catalogStatusLabel}</p>
          ) : null}
          <p className="line-clamp-2 text-[13px] font-semibold leading-snug text-[#1a1a1a]">
            {detailQuery.data.title}
          </p>
        </div>
        <ul className="flex flex-col gap-2">
          {canUpdate ? (
            <MobileActionRow
              icon={Pencil}
              label="Modifier"
              tone="neutral"
              onClick={() => onNavigate(`/action-plans/${actionPlanId}/edit`)}
            />
          ) : null}
          {canActivate ? (
            <MobileActionRow
              icon={Power}
              label="Activer"
              tone="neutral"
              disabled={activateMutation.isPending}
              onClick={() => void handleActivate()}
            />
          ) : null}
          {canDeactivate ? (
            <MobileActionRow
              icon={Ban}
              label="Désactiver"
              tone="danger"
              disabled={deactivateMutation.isPending}
              onClick={() => void handleDeactivate()}
            />
          ) : null}
          {canDelete ? (
            <MobileActionRow
              icon={Trash2}
              label="Supprimer"
              tone="danger"
              disabled={deleteMutation.isPending}
              onClick={() => void handleDelete()}
            />
          ) : null}
        </ul>
        {actionError ? (
          <p className="mt-2 px-1 text-sm text-destructive" role="alert">
            {actionError}
          </p>
        ) : null}
      </TerrainBottomSheet>
    </>
  )
}
