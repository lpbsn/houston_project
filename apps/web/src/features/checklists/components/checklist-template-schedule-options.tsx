import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'
import { createPortal } from 'react-dom'

import { TerrainCard, TerrainSectionLabel, TerrainStickyFooter } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import type { ScopedUserSearchResult } from '@/features/actions/types'
import { ChecklistAssigneeSheet } from '@/features/checklists/components/checklist-assignee-sheet'
import { ChecklistDateSheet } from '@/features/checklists/components/checklist-date-sheet'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import { ChecklistOptionRow } from '@/features/checklists/components/checklist-option-row'
import { ChecklistRecurrenceSheet } from '@/features/checklists/components/checklist-recurrence-sheet'
import { ChecklistTimeSheet } from '@/features/checklists/components/checklist-time-sheet'
import { useScheduleChecklistFromTemplateMutation } from '@/features/checklists/hooks'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import { buildChecklistTemplateSchedulePayload } from '@/features/checklists/lib/checklist-template-schedule-payload'
import {
  formatScheduleDateLabel,
  formatScheduleTimeLabel,
  getScheduleAssigneeLabel,
  getScheduleModeUnavailableMessage,
  getScheduleRecurrenceLabel,
  getScheduleReferenceDateIso,
  getScheduleSubmitLabel,
  isRecurringSchedule,
} from '@/features/checklists/lib/checklist-template-schedule-form'
import {
  canAssignChecklistExecutionToOthers,
  canShowChecklistTemplateCreateAssignment,
  canShowChecklistTemplateLaunchExecution,
  type ChecklistTemplatePermissionHints,
} from '@/features/checklists/lib/checklist-template-permission-hints'
import {
  hasTemplateScheduleFormErrors,
  validateTemplateScheduleForm,
} from '@/features/checklists/lib/checklist-form-validation'

type OpenSheet = 'assignee' | 'start' | 'end' | 'recurrence' | 'recurrence_end' | null

type ChecklistTemplateScheduleOptionsProps = {
  establishmentId: string
  templateId: string
  businessUnitId: string
  permissionHints: ChecklistTemplatePermissionHints
  activeMembershipId: string
  activeMembershipDisplayName?: string | null
  establishmentLocalDateIso?: string | null
  footerHost?: HTMLElement | null
  onExecutionCreated: (executionId: string) => void
  onAssignmentCreated: () => void
}

export function ChecklistTemplateScheduleOptions({
  establishmentId,
  templateId,
  businessUnitId,
  permissionHints,
  activeMembershipId,
  activeMembershipDisplayName,
  establishmentLocalDateIso,
  footerHost,
  onExecutionCreated,
  onAssignmentCreated,
}: ChecklistTemplateScheduleOptionsProps) {
  const canLaunchExecution = canShowChecklistTemplateLaunchExecution(permissionHints)
  const canCreateAssignment = canShowChecklistTemplateCreateAssignment(permissionHints)
  const canAssignToOthers = canAssignChecklistExecutionToOthers(permissionHints)
  const referenceDateIso = getScheduleReferenceDateIso(establishmentLocalDateIso)

  const [assignedTo, setAssignedTo] = useState(activeMembershipId)
  const [selectedUser, setSelectedUser] = useState<ScopedUserSearchResult | null>(null)
  const [startAt, setStartAt] = useState('')
  const [endAt, setEndAt] = useState('')
  const [recurrenceDays, setRecurrenceDays] = useState<string[]>([])
  const [recurrenceEndDate, setRecurrenceEndDate] = useState('')
  const [openSheet, setOpenSheet] = useState<OpenSheet>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [apiError, setApiError] = useState<string | null>(null)

  const scheduleMutation = useScheduleChecklistFromTemplateMutation(establishmentId, templateId)
  const isPending = scheduleMutation.isPending
  const isRecurring = isRecurringSchedule(recurrenceDays)
  const submitLabel = getScheduleSubmitLabel(recurrenceDays)
  const canSubmitMode = isRecurring ? canCreateAssignment : canLaunchExecution
  const modeUnavailableMessage = !canSubmitMode
    ? getScheduleModeUnavailableMessage(isRecurring)
    : null

  function clearFieldError(field: string) {
    setFieldErrors((prev) => ({ ...prev, [field]: '' }))
  }

  function handleTimeApply(target: 'start' | 'end', hours: string, minutes: string) {
    const value = `${hours}:${minutes}`
    if (target === 'start') {
      setStartAt(value)
      clearFieldError('startAt')
    } else {
      setEndAt(value)
      clearFieldError('endAt')
    }
  }

  async function handleSubmit() {
    if (isPending) {
      return
    }

    const errors = validateTemplateScheduleForm(
      {
        assignedTo,
        startAt,
        endAt,
        recurrenceDays,
        recurrenceEndDate,
        canLaunchExecution,
        canCreateAssignment,
      },
      { referenceDateIso },
    )

    if (hasTemplateScheduleFormErrors(errors)) {
      setFieldErrors(errors)
      return
    }

    setFieldErrors({})
    setApiError(null)

    try {
      const response = await scheduleMutation.mutateAsync(
        buildChecklistTemplateSchedulePayload({
          assignedTo,
          startAt,
          endAt,
          recurrenceDays,
          recurrenceEndDate,
        }),
      )

      if (response.result_type === 'execution' && response.execution?.id) {
        onExecutionCreated(response.execution.id)
        return
      }

      if (response.result_type === 'assignment') {
        onAssignmentCreated()
      }
    } catch (error) {
      setApiError(
        resolveChecklistErrorMessage(error, 'La planification n’a pas pu être enregistrée.'),
      )
    }
  }

  const stickyFooter = (
    <TerrainStickyFooter>
      {modeUnavailableMessage ? (
        <p className="mb-2 text-xs text-[#7D7B75]" role="status">
          {modeUnavailableMessage}
        </p>
      ) : null}
      <Button
        type="button"
        className="h-11 w-full rounded-xl bg-[#1B4FD8]"
        disabled={isPending || !canSubmitMode}
        onClick={() => void handleSubmit()}
      >
        {isPending ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" aria-hidden /> : null}
        {submitLabel}
      </Button>
    </TerrainStickyFooter>
  )

  return (
    <>
      <section className="space-y-1.5">
        <TerrainSectionLabel>Planification</TerrainSectionLabel>
        <TerrainCard className="divide-y divide-[#F0EFE9] p-0">
          <ChecklistOptionRow
            label="Attribuer à"
            value={getScheduleAssigneeLabel({
              assignedTo,
              activeMembershipId,
              selectedUser,
              activeMembershipDisplayName,
            })}
            onClick={canAssignToOthers ? () => setOpenSheet('assignee') : undefined}
            disabled={!canAssignToOthers}
            error={fieldErrors.assignedTo}
          />
          <ChecklistOptionRow
            label="Début"
            value={formatScheduleTimeLabel(startAt)}
            onClick={() => setOpenSheet('start')}
            error={fieldErrors.startAt}
            ariaLabel="Début"
          />
          <ChecklistOptionRow
            label="Fin"
            value={formatScheduleTimeLabel(endAt)}
            onClick={() => setOpenSheet('end')}
            error={fieldErrors.endAt}
            ariaLabel="Fin"
          />
          <ChecklistOptionRow
            label="Récurrence"
            value={getScheduleRecurrenceLabel(recurrenceDays)}
            onClick={canCreateAssignment ? () => setOpenSheet('recurrence') : undefined}
            disabled={!canCreateAssignment}
            error={fieldErrors.recurrenceDays}
          />
          {isRecurring ? (
            <ChecklistOptionRow
              label="Fin de la récurrence"
              value={formatScheduleDateLabel(recurrenceEndDate)}
              onClick={() => setOpenSheet('recurrence_end')}
              error={fieldErrors.recurrenceEndDate}
            />
          ) : null}
        </TerrainCard>

        {apiError ? <ChecklistFeedback variant="error" message={apiError} /> : null}
        {fieldErrors.submit ? (
          <ChecklistFeedback variant="error" message={fieldErrors.submit} />
        ) : null}
      </section>

      {footerHost ? createPortal(stickyFooter, footerHost) : stickyFooter}

      {openSheet === 'assignee' ? (
        <ChecklistAssigneeSheet
          establishmentId={establishmentId}
          businessUnitId={businessUnitId}
          assignedTo={assignedTo}
          selectedUser={selectedUser}
          onClose={() => setOpenSheet(null)}
          onApply={(membershipId, user) => {
            setAssignedTo(membershipId)
            setSelectedUser(user)
            clearFieldError('assignedTo')
          }}
        />
      ) : null}

      {openSheet === 'start' ? (
        <ChecklistTimeSheet
          key={`start-${startAt}`}
          title="Début"
          timeValue={startAt}
          onClose={() => setOpenSheet(null)}
          onApply={(hours, minutes) => handleTimeApply('start', hours, minutes)}
        />
      ) : null}

      {openSheet === 'end' ? (
        <ChecklistTimeSheet
          key={`end-${endAt}`}
          title="Fin"
          timeValue={endAt}
          onClose={() => setOpenSheet(null)}
          onApply={(hours, minutes) => handleTimeApply('end', hours, minutes)}
        />
      ) : null}

      {openSheet === 'recurrence' ? (
        <ChecklistRecurrenceSheet
          recurrenceDays={recurrenceDays}
          onClose={() => setOpenSheet(null)}
          onApply={(days) => {
            setRecurrenceDays(days)
            clearFieldError('recurrenceDays')
            if (days.length === 0) {
              setRecurrenceEndDate('')
              clearFieldError('recurrenceEndDate')
            }
          }}
        />
      ) : null}

      {openSheet === 'recurrence_end' ? (
        <ChecklistDateSheet
          title="Fin de la récurrence"
          value={recurrenceEndDate}
          minDate={referenceDateIso}
          onClose={() => setOpenSheet(null)}
          onApply={(value) => {
            setRecurrenceEndDate(value)
            clearFieldError('recurrenceEndDate')
          }}
        />
      ) : null}
    </>
  )
}
