import { LoaderCircle } from 'lucide-react'
import { useCallback } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { ChecklistAssignmentFormFields } from '@/features/checklists/components/checklist-assignment-form-fields'
import { useCreateChecklistAssignmentMutation } from '@/features/checklists/hooks'
import { buildChecklistAssignmentCreatePayload } from '@/features/checklists/lib/checklist-assignment-create-payload'
import {
  EMPTY_ASSIGNMENT_FORM_VALUES,
  useChecklistAssignmentForm,
} from '@/features/checklists/lib/checklist-assignment-form'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import type { ChecklistType } from '@/features/checklists/types'

type ChecklistAssignmentCreateSheetProps = {
  open: boolean
  establishmentId: string
  templateId: string
  checklistType: ChecklistType
  businessUnitId: string
  onClose: () => void
  onSuccess: () => void
}

export function ChecklistAssignmentCreateSheet({
  open,
  establishmentId,
  templateId,
  checklistType,
  businessUnitId,
  onClose,
  onSuccess,
}: ChecklistAssignmentCreateSheetProps) {
  const createMutation = useCreateChecklistAssignmentMutation(
    establishmentId,
    templateId,
    checklistType,
  )

  const {
    assignedTo,
    setAssignedTo,
    selectedUser,
    setSelectedUser,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    startAt,
    setStartAt,
    endAt,
    setEndAt,
    recurrenceDays,
    setRecurrenceDays,
    fieldErrors,
    setFieldErrors,
    apiError,
    setApiError,
    resetForm,
    clearFieldError,
    validateForm,
    getFormValues,
    hasAssignmentFormErrors,
  } = useChecklistAssignmentForm()
  const isPending = createMutation.isPending

  const handleClose = useCallback(() => {
    resetForm(EMPTY_ASSIGNMENT_FORM_VALUES, null)
    onClose()
  }, [onClose, resetForm])

  function handleSheetCloseRequest() {
    if (isPending) {
      return
    }
    handleClose()
  }

  async function handleCreateAssignment() {
    const errors = validateForm()

    if (hasAssignmentFormErrors(errors)) {
      setFieldErrors(errors)
      return
    }

    setFieldErrors({})
    setApiError(null)

    try {
      await createMutation.mutateAsync(
        buildChecklistAssignmentCreatePayload(getFormValues()),
      )
      handleClose()
      onSuccess()
    } catch (error) {
      setApiError(
        resolveChecklistErrorMessage(error, 'L’affectation n’a pas pu être créée.'),
      )
    }
  }

  return (
    <TerrainBottomSheet
      title="Nouvelle affectation"
      open={open}
      onClose={handleSheetCloseRequest}
      footer={
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            className="flex-1"
            disabled={isPending}
            onClick={handleSheetCloseRequest}
          >
            Annuler
          </Button>
          <Button
            type="button"
            className="flex-1 bg-[#1B4FD8]"
            disabled={isPending}
            onClick={() => void handleCreateAssignment()}
          >
            {isPending ? (
              <LoaderCircle className="mr-2 h-4 w-4 animate-spin" aria-hidden />
            ) : null}
            Créer l’affectation
          </Button>
        </div>
      }
    >
      <ChecklistAssignmentFormFields
        idPrefix="assignment-sheet"
        establishmentId={establishmentId}
        businessUnitId={businessUnitId}
        assignedTo={assignedTo}
        selectedUser={selectedUser}
        onAssignedToChange={(membershipId, user) => {
          setAssignedTo(membershipId)
          setSelectedUser(user)
          clearFieldError('assignedTo')
        }}
        startDate={startDate}
        onStartDateChange={(value) => {
          setStartDate(value)
          clearFieldError('startDate')
        }}
        endDate={endDate}
        onEndDateChange={(value) => {
          setEndDate(value)
          clearFieldError('endDate')
        }}
        startAt={startAt}
        onStartAtChange={(value) => {
          setStartAt(value)
          clearFieldError('startAt')
        }}
        endAt={endAt}
        onEndAtChange={(value) => {
          setEndAt(value)
          clearFieldError('endAt')
        }}
        recurrenceDays={recurrenceDays}
        onRecurrenceDaysChange={setRecurrenceDays}
        fieldErrors={fieldErrors}
        apiError={apiError}
      />
    </TerrainBottomSheet>
  )
}
