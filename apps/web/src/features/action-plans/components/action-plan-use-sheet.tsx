import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanEventPlanningForm } from './action-plan-event-planning-form'
import {
  createActionPlanEventPlanningDraft,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import {
  CATALOG_LAUNCH_EXECUTION_LABEL,
  isCatalogPlanningPrimaryDisabled,
  resolveCatalogPlanningSubmit,
  validateCatalogPlanningDraft,
  type CatalogPlanningSubmit,
} from '../lib/action-plan-catalog-planning-submit'

type ActionPlanUseSheetProps = {
  open: boolean
  establishmentId: string
  pilotBusinessUnitId: string
  isPending: boolean
  staffUseMode?: boolean
  staffDisplayName?: string
  canSchedule?: boolean
  onClose: () => void
  onPlanningSubmit: (result: CatalogPlanningSubmit) => void
}

type ActionPlanUseSheetBodyProps = Omit<ActionPlanUseSheetProps, 'open'>

export function ActionPlanUseSheet({ open, ...rest }: ActionPlanUseSheetProps) {
  if (!open) {
    return null
  }

  return <ActionPlanUseSheetBody {...rest} />
}

function ActionPlanUseSheetBody({
  establishmentId,
  pilotBusinessUnitId,
  isPending,
  staffUseMode = false,
  staffDisplayName = 'Moi',
  canSchedule = false,
  onClose,
  onPlanningSubmit,
}: ActionPlanUseSheetBodyProps) {
  const [planningDraft, setPlanningDraft] = useState<ActionPlanEventPlanningDraft>(
    createActionPlanEventPlanningDraft,
  )
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const planningOptions = { canSchedule, staffMode: staffUseMode }
  const primaryDisabled = isCatalogPlanningPrimaryDisabled(planningDraft, {
    ...planningOptions,
    isPending,
  })

  function handlePrimaryAction() {
    const errors = validateCatalogPlanningDraft(planningDraft, planningOptions)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }

    const submit = resolveCatalogPlanningSubmit(planningDraft, planningOptions)
    if (!submit) {
      return
    }

    onPlanningSubmit(submit)
  }

  return (
    <TerrainBottomSheet
      title="Utiliser ce plan"
      open
      onClose={onClose}
      footer={
        <Button
          type="button"
          className={cn(
            'h-11 w-full rounded-xl text-white',
            terrainBrandAction.bg,
            terrainBrandAction.hover,
          )}
          disabled={primaryDisabled}
          onClick={handlePrimaryAction}
        >
          {CATALOG_LAUNCH_EXECUTION_LABEL}
        </Button>
      }
    >
      <ActionPlanEventPlanningForm
        draft={planningDraft}
        config={{
          canEditAssignees: !staffUseMode,
          canSchedule,
          staffMode: staffUseMode,
          showAdvancedChronology: !staffUseMode,
          hideAssignees: false,
          staffDisplayName,
          assigneeActionsEnabled: false,
        }}
        establishmentId={establishmentId}
        pilotBusinessUnitId={pilotBusinessUnitId}
        fieldErrors={fieldErrors}
        onDraftChange={setPlanningDraft}
      />
    </TerrainBottomSheet>
  )
}
