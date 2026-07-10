import { Plus } from 'lucide-react'

import { TerrainStickyFooter } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'

import type { ActionPlanPermissionHints } from '../types'
import {
  canShowActionPlanActivate,
  canShowActionPlanDeactivate,
  canShowActionPlanUse,
} from '../lib/action-plan-permission-hints'

type ActionPlanTemplateDetailStickyFooterProps = {
  hints: ActionPlanPermissionHints
  executionPanelOpen: boolean
  canUpdate: boolean
  canUse: boolean
  isBusy: boolean
  isLaunchPending: boolean
  onNavigateToEdit: () => void
  onActivate: () => void
  onDeactivate: () => void
  onOpenExecutionPanel: () => void
  onCloseExecutionPanel: () => void
  onLaunchExecution: () => void
}

export function ActionPlanTemplateDetailStickyFooter({
  hints,
  executionPanelOpen,
  canUpdate,
  canUse,
  isBusy,
  isLaunchPending,
  onNavigateToEdit,
  onActivate,
  onDeactivate,
  onOpenExecutionPanel,
  onCloseExecutionPanel,
  onLaunchExecution,
}: ActionPlanTemplateDetailStickyFooterProps) {
  if (executionPanelOpen) {
    return (
      <TerrainStickyFooter>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            className="h-11 flex-1 rounded-xl"
            disabled={isLaunchPending}
            onClick={onCloseExecutionPanel}
          >
            Annuler
          </Button>
          <Button
            type="button"
            className="h-11 flex-1 rounded-xl"
            disabled={isLaunchPending}
            onClick={onLaunchExecution}
          >
            Lancer l&apos;exécution
          </Button>
        </div>
      </TerrainStickyFooter>
    )
  }

  const showActivate = canShowActionPlanActivate(hints)
  const showDeactivate = canShowActionPlanDeactivate(hints)
  const showUse = canUse && canShowActionPlanUse(hints)

  if (!canUpdate && !showActivate && !showDeactivate && !showUse) {
    return null
  }

  return (
    <TerrainStickyFooter className="flex flex-col gap-2">
      {canUpdate ? (
        <Button
          type="button"
          variant="outline"
          className="h-11 w-full rounded-xl"
          disabled={isBusy}
          onClick={onNavigateToEdit}
        >
          Modifier
        </Button>
      ) : null}
      {showActivate ? (
        <Button
          type="button"
          variant="outline"
          className="h-11 w-full rounded-xl"
          disabled={isBusy}
          onClick={onActivate}
        >
          Activer dans la bibliothèque
        </Button>
      ) : null}
      {showDeactivate ? (
        <Button
          type="button"
          variant="outline"
          className="h-11 w-full rounded-xl text-[#E24B4A]"
          disabled={isBusy}
          onClick={onDeactivate}
        >
          Désactiver
        </Button>
      ) : null}
      {showUse ? (
        <Button
          type="button"
          className="h-11 w-full rounded-xl"
          disabled={isBusy}
          onClick={onOpenExecutionPanel}
        >
          <Plus className="mr-2 h-4 w-4" aria-hidden />
          Exécution
        </Button>
      ) : null}
    </TerrainStickyFooter>
  )
}
