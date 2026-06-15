import { ChevronRight } from 'lucide-react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { ChecklistAssignmentFormFields } from '@/features/checklists/components/checklist-assignment-form-fields'
import type { ChecklistCreateAssignmentMode } from '@/features/checklists/lib/checklist-create-submit'
import {
  hasAssignmentFormErrors,
  validateAssignmentForm,
} from '@/features/checklists/lib/checklist-form-validation'
import type { ScopedUserSearchResult } from '@/features/actions/types'
import { cn } from '@/lib/utils'

type ChecklistCreateOptionsSheetProps = {
  open: boolean
  flashEnabled: boolean
  establishmentId: string
  businessUnitId: string
  assignmentMode: ChecklistCreateAssignmentMode
  onAssignmentModeChange: (mode: ChecklistCreateAssignmentMode) => void
  assignedTo: string
  selectedUser: ScopedUserSearchResult | null
  onAssignedToChange: (membershipId: string, user: ScopedUserSearchResult | null) => void
  startDate: string
  onStartDateChange: (value: string) => void
  endDate: string
  onEndDateChange: (value: string) => void
  startAt: string
  onStartAtChange: (value: string) => void
  endAt: string
  onEndAtChange: (value: string) => void
  recurrenceDays: string[]
  onRecurrenceDaysChange: (value: string[]) => void
  fieldErrors: Record<string, string>
  onFieldErrorsChange: (errors: Record<string, string>) => void
  onClose: () => void
  onSave: () => void
}

function assignmentModeButtonClass(isSelected: boolean): string {
  return cn(
    'rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
    isSelected ? 'bg-[#EEF2FF] text-[#1B4FD8]' : 'bg-[#F0EFE9] text-[#7D7B75]',
  )
}

export function ChecklistCreateOptionsSheet({
  open,
  flashEnabled,
  establishmentId,
  businessUnitId,
  assignmentMode,
  onAssignmentModeChange,
  assignedTo,
  selectedUser,
  onAssignedToChange,
  startDate,
  onStartDateChange,
  endDate,
  onEndDateChange,
  startAt,
  onStartAtChange,
  endAt,
  onEndAtChange,
  recurrenceDays,
  onRecurrenceDaysChange,
  fieldErrors,
  onFieldErrorsChange,
  onClose,
  onSave,
}: ChecklistCreateOptionsSheetProps) {
  function handleSave() {
    const errors: Record<string, string> = {}

    if (!flashEnabled && assignmentMode === 'create_now') {
      const assignmentErrors = validateAssignmentForm({
        assignedTo,
        startDate,
        endDate: recurrenceDays.length > 0 ? endDate : startDate,
        startAt,
        endAt,
        recurrenceDays,
      })
      Object.assign(errors, assignmentErrors)
    }

    if (Object.keys(errors).length > 0) {
      onFieldErrorsChange(errors)
      return
    }

    onFieldErrorsChange({})
    onSave()
  }

  return (
    <TerrainBottomSheet
      title="Options"
      open={open}
      onClose={onClose}
      footer={
        <div className="flex gap-2">
          <Button type="button" variant="outline" className="flex-1" onClick={onClose}>
            Fermer
          </Button>
          <Button
            type="button"
            className="flex-1 bg-[#1B4FD8]"
            onClick={handleSave}
          >
            Enregistrer
          </Button>
        </div>
      }
    >
      <div className="space-y-4 pb-2">
        {!flashEnabled ? (
          <section className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-[#7D7B75]">
              Affectation
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className={assignmentModeButtonClass(assignmentMode === 'none')}
                onClick={() => onAssignmentModeChange('none')}
              >
                Sans affectation
              </button>
              <button
                type="button"
                className={assignmentModeButtonClass(assignmentMode === 'create_now')}
                onClick={() => onAssignmentModeChange('create_now')}
              >
                Créer une affectation maintenant
              </button>
            </div>

            {assignmentMode === 'create_now' ? (
              <ChecklistAssignmentFormFields
                idPrefix="create-options"
                establishmentId={establishmentId}
                businessUnitId={businessUnitId}
                assignedTo={assignedTo}
                selectedUser={selectedUser}
                onAssignedToChange={(membershipId, user) => {
                  onAssignedToChange(membershipId, user)
                  onFieldErrorsChange({ ...fieldErrors, assignedTo: '' })
                }}
                startDate={startDate}
                onStartDateChange={(value) => {
                  onStartDateChange(value)
                  onFieldErrorsChange({ ...fieldErrors, startDate: '' })
                }}
                endDate={endDate}
                onEndDateChange={(value) => {
                  onEndDateChange(value)
                  onFieldErrorsChange({ ...fieldErrors, endDate: '' })
                }}
                startAt={startAt}
                onStartAtChange={(value) => {
                  onStartAtChange(value)
                  onFieldErrorsChange({ ...fieldErrors, startAt: '' })
                }}
                endAt={endAt}
                onEndAtChange={(value) => {
                  onEndAtChange(value)
                  onFieldErrorsChange({ ...fieldErrors, endAt: '' })
                }}
                recurrenceDays={recurrenceDays}
                onRecurrenceDaysChange={onRecurrenceDaysChange}
                fieldErrors={fieldErrors}
              />
            ) : null}
          </section>
        ) : null}
      </div>
    </TerrainBottomSheet>
  )
}

type ChecklistCreateOptionsButtonProps = {
  assignmentSummary: string
  onClick: () => void
}

export function ChecklistCreateOptionsButton({
  assignmentSummary,
  onClick,
}: ChecklistCreateOptionsButtonProps) {
  return (
    <button
      type="button"
      aria-label="Options"
      className="flex min-h-11 w-full items-center justify-between rounded-xl border border-[#E8E6DF] bg-white px-3 py-2.5 text-left"
      onClick={onClick}
    >
      <div className="min-w-0">
        <p className="text-sm font-medium text-[#1a1a1a]">Options</p>
        <p className="truncate text-xs text-[#7D7B75]">{assignmentSummary}</p>
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-[#7D7B75]" aria-hidden />
    </button>
  )
}

export function hasOptionsSheetErrors(errors: Record<string, string>): boolean {
  return hasAssignmentFormErrors(errors)
}
