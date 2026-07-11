import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'

import { ActionPlanEventPlanningForm } from './action-plan-event-planning-form'
import {
  buildScheduleRequestsFromDraft,
  buildUseRequestFromDraft,
  createActionPlanEventPlanningDraft,
  hasGlobalRepeat,
  shouldHidePrimaryPlanningActions,
  toScheduleDraft,
  validateActionPlanEventPlanningDraft,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import { isActionPlanScheduleConfigured } from '../lib/action-plan-schedule-form'
import type { ActionPlanScheduleCreateRequest, ActionPlanUseRequest } from '../types'

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
  onConfirm: (body: ReturnType<typeof buildUseRequestFromDraft>) => void
  onScheduleConfirm?: (body: ActionPlanScheduleCreateRequest) => void
  onAssigneeSchedule?: (assigneeId: string, body: ActionPlanScheduleCreateRequest) => void
  onAssigneeLaunch?: (assigneeId: string, body: ActionPlanUseRequest) => void
  assigneeActionPending?: Record<string, 'schedule' | 'launch'>
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
  onAssigneeSchedule,
  onAssigneeLaunch,
  assigneeActionPending = {},
}: ActionPlanUseSheetBodyProps) {
  const [planningDraft, setPlanningDraft] = useState<ActionPlanEventPlanningDraft>(
    createActionPlanEventPlanningDraft,
  )
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const scheduleConfigured = isActionPlanScheduleConfigured(toScheduleDraft(planningDraft))

  const isRepeatSubmit = hasGlobalRepeat(planningDraft) && canSchedule
  const hidePrimaryFooter = shouldHidePrimaryPlanningActions(planningDraft)

  function handlePrimaryAction() {
    if (shouldHidePrimaryPlanningActions(planningDraft)) {
      return
    }

    const errors = validateActionPlanEventPlanningDraft(planningDraft, {
      requireAssignees: false,
      allowRepeat: canSchedule,
    })
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }

    if (isRepeatSubmit) {
      const schedules = buildScheduleRequestsFromDraft(planningDraft, {
        staffMode: staffUseMode,
      })
      const body = schedules[0]
      if (!body || !onScheduleConfirm) {
        return
      }
      onScheduleConfirm(body)
      return
    }

    onConfirm(
      buildUseRequestFromDraft(planningDraft, {
        staffMode: staffUseMode,
      }),
    )
  }

  const primaryLabel = isRepeatSubmit ? 'Planifier la récurrence' : "Lancer l'exécution"
  const primaryPending = isRepeatSubmit ? isSchedulePending : isPending
  const primaryDisabled = isRepeatSubmit ? !scheduleConfigured || primaryPending : primaryPending

  return (
    <TerrainBottomSheet
      title="Utiliser ce plan"
      open
      onClose={onClose}
      footer={
        hidePrimaryFooter ? undefined : (
          <Button
            type="button"
            className="h-11 w-full rounded-xl"
            disabled={primaryDisabled}
            onClick={handlePrimaryAction}
          >
            {primaryLabel}
          </Button>
        )
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
          assigneeActionsEnabled: true,
          assigneeActionPending,
        }}
        establishmentId={establishmentId}
        pilotBusinessUnitId={pilotBusinessUnitId}
        fieldErrors={fieldErrors}
        onDraftChange={setPlanningDraft}
        onAssigneeSchedule={onAssigneeSchedule}
        onAssigneeLaunch={onAssigneeLaunch}
      />
    </TerrainBottomSheet>
  )
}
