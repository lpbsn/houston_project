import { useEffect, useMemo, useRef, useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanEventPlanningForm } from './action-plan-event-planning-form'
import {
  createActionPlanEventPlanningDraft,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import { guideToFirstActionPlanFieldError } from '../lib/action-plan-form-guidance'
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
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false)
  const [guidanceNonce, setGuidanceNonce] = useState(0)
  const formRootRef = useRef<HTMLDivElement>(null)
  const lastGuidanceNonceRef = useRef(0)

  const frontendFieldErrors = useMemo(
    () =>
      hasAttemptedSubmit
        ? validateCatalogPlanningDraft(planningDraft, {
            canSchedule,
            staffMode: staffUseMode,
          })
        : {},
    [hasAttemptedSubmit, planningDraft, canSchedule, staffUseMode],
  )
  const planningOptions = { canSchedule, staffMode: staffUseMode }
  const primaryDisabled = isCatalogPlanningPrimaryDisabled(planningDraft, {
    ...planningOptions,
    isPending,
  })

  useEffect(() => {
    if (guidanceNonce <= lastGuidanceNonceRef.current) {
      return
    }
    lastGuidanceNonceRef.current = guidanceNonce
    if (Object.keys(frontendFieldErrors).length === 0) {
      return
    }
    return guideToFirstActionPlanFieldError(frontendFieldErrors, {
      root: formRootRef.current ?? document,
    })
  }, [frontendFieldErrors, guidanceNonce])

  function handlePrimaryAction() {
    setHasAttemptedSubmit(true)
    const errors = validateCatalogPlanningDraft(planningDraft, planningOptions)
    if (Object.keys(errors).length > 0) {
      setGuidanceNonce((value) => value + 1)
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
      <div ref={formRootRef}>
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
          fieldErrors={frontendFieldErrors}
          onDraftChange={(update) => {
            setPlanningDraft((previous) =>
              typeof update === 'function' ? update(previous) : update,
            )
          }}
        />
      </div>
    </TerrainBottomSheet>
  )
}
