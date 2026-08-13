import { Plus } from 'lucide-react'

import { TerrainStickyFooter } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import type { ActionPlanPermissionHints } from '../types'
import { canShowActionPlanUse } from '../lib/action-plan-permission-hints'
import { CATALOG_LAUNCH_EXECUTION_LABEL } from '../lib/action-plan-catalog-planning-submit'

const catalogPrimaryButtonClassName = cn(
  'text-white',
  terrainBrandAction.bg,
  terrainBrandAction.hover,
)

type ActionPlanTemplateDetailStickyFooterProps = {
  hints: ActionPlanPermissionHints
  executionPanelOpen: boolean
  canUse: boolean
  isBusy: boolean
  primaryActionDisabled: boolean
  isPrimaryPending: boolean
  onOpenExecutionPanel: () => void
  onCloseExecutionPanel: () => void
  onLaunchExecution: () => void
  className?: string
}

export function ActionPlanTemplateDetailStickyFooter({
  className,
  hints,
  executionPanelOpen,
  canUse,
  isBusy,
  primaryActionDisabled,
  isPrimaryPending,
  onOpenExecutionPanel,
  onCloseExecutionPanel,
  onLaunchExecution,
}: ActionPlanTemplateDetailStickyFooterProps) {
  if (executionPanelOpen) {
    return (
      <TerrainStickyFooter className={className}>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            className="h-11 flex-1 rounded-xl"
            disabled={isPrimaryPending}
            onClick={onCloseExecutionPanel}
          >
            Annuler
          </Button>
          <Button
            type="button"
            className={cn('h-11 flex-1 rounded-full', catalogPrimaryButtonClassName)}
            disabled={primaryActionDisabled}
            onClick={onLaunchExecution}
          >
            {CATALOG_LAUNCH_EXECUTION_LABEL}
          </Button>
        </div>
      </TerrainStickyFooter>
    )
  }

  const showUse = canUse && canShowActionPlanUse(hints)

  if (!showUse) {
    return null
  }

  return (
    <TerrainStickyFooter className={cn('flex flex-col gap-2', className)}>
      <Button
        type="button"
        className={cn('h-11 w-full rounded-full', catalogPrimaryButtonClassName)}
        disabled={isBusy}
        onClick={onOpenExecutionPanel}
      >
        <Plus className="mr-2 h-4 w-4" aria-hidden />
        Exécution
      </Button>
    </TerrainStickyFooter>
  )
}
