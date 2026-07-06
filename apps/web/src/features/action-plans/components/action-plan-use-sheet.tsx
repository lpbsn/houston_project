import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'

import { ActionPlanEventPlanningForm } from './action-plan-event-planning-form'
import { buildActionPlanUseRequest } from '../lib/action-plan-create-payload'
import {
  createActionPlanEventPlanningDraft,
  toScheduleDraft,
  toUseRequestOptions,
  validateActionPlanEventPlanningDraft,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import { buildActionPlanScheduleCreateRequest } from '../lib/action-plan-schedule-payload'
import { isActionPlanScheduleConfigured } from '../lib/action-plan-schedule-form'
import type { ActionPlanScheduleCreateRequest } from '../types'

type ActionPlanUseSheetProps = {
  open: boolean
  establishmentId: string
  pilotBusinessUnitId: string
  isPending: boolean
  isSchedulePending?: boolean
  staffUseMode?: boolean
  staffDisplayName?: string
  canSchedule?: boolean
  onClose: () => void
  onConfirm: (body: ReturnType<typeof buildActionPlanUseRequest>) => void
  onScheduleConfirm?: (body: ActionPlanScheduleCreateRequest) => void
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
  isSchedulePending = false,
  staffUseMode = false,
  staffDisplayName = 'Moi',
  canSchedule = false,
  onClose,
  onConfirm,
  onScheduleConfirm,
}: ActionPlanUseSheetBodyProps) {
  const [planningDraft, setPlanningDraft] = useState<ActionPlanEventPlanningDraft>(
    createActionPlanEventPlanningDraft,
  )
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const scheduleConfigured = isActionPlanScheduleConfigured(toScheduleDraft(planningDraft))

  const isRepeatSubmit = planningDraft.repeatEnabled && canSchedule

  function handlePrimaryAction() {
    const errors = validateActionPlanEventPlanningDraft(planningDraft, {
      requireAssignees: false,
      allowRepeat: canSchedule,
    })
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }

    if (isRepeatSubmit) {
      const body = buildActionPlanScheduleCreateRequest({
        schedule: toScheduleDraft(planningDraft),
        assignees: staffUseMode ? [] : planningDraft.assignees,
        useSharedChronology: !planningDraft.usePerAssigneeChronology,
      })
      if (!body || !onScheduleConfirm) {
        return
      }
      onScheduleConfirm(body)
      return
    }

    const useOptions = toUseRequestOptions(planningDraft)
    onConfirm(
      buildActionPlanUseRequest({
        ...useOptions,
        assignees: staffUseMode ? [] : useOptions.assignees,
      }),
    )
  }

  const primaryLabel = isRepeatSubmit ? 'Planifier la récurrence' : "Lancer l'exécution"
  const primaryPending = isRepeatSubmit ? isSchedulePending : isPending
  const primaryDisabled =
    isRepeatSubmit ? !scheduleConfigured || primaryPending : primaryPending

  return (
    <TerrainBottomSheet
      title="Utiliser ce plan"
      open
      onClose={onClose}
      footer={
        <Button
          type="button"
          className="h-11 w-full rounded-xl"
          disabled={primaryDisabled}
          onClick={handlePrimaryAction}
        >
          {primaryLabel}
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
        }}
        establishmentId={establishmentId}
        pilotBusinessUnitId={pilotBusinessUnitId}
        fieldErrors={fieldErrors}
        onDraftChange={setPlanningDraft}
      />
    </TerrainBottomSheet>
  )
}
