import { LoaderCircle } from 'lucide-react'
import { useCallback } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { ChecklistAssignmentFormFields } from '@/features/checklists/components/checklist-assignment-form-fields'
import { useUpdateChecklistAssignmentMutation } from '@/features/checklists/hooks'
import {
  assignmentToFormValues,
  buildChecklistAssignmentUpdatePayload,
} from '@/features/checklists/lib/checklist-assignment-create-payload'
import {
  buildInitialSelectedUser,
  useChecklistAssignmentForm,
} from '@/features/checklists/lib/checklist-assignment-form'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import type { ChecklistAssignment } from '@/features/checklists/types'

type ChecklistAssignmentEditSheetProps = {
  open: boolean
  establishmentId: string
  templateId: string
  businessUnitId: string
  assignment: ChecklistAssignment
  onClose: () => void
  onSuccess: () => void
}

export function ChecklistAssignmentEditSheet({
  open,
  establishmentId,
  templateId,
  businessUnitId,
  assignment,
  onClose,
  onSuccess,
}: ChecklistAssignmentEditSheetProps) {
  const initialValues = assignmentToFormValues(assignment)
  const updateMutation = useUpdateChecklistAssignmentMutation(establishmentId, templateId)

  const initialSelectedUser = buildInitialSelectedUser(assignment)
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
  } = useChecklistAssignmentForm({
    initialValues,
    initialSelectedUser,
  })
  const isPending = updateMutation.isPending

  const handleClose = useCallback(() => {
    resetForm(initialValues, initialSelectedUser)
    onClose()
  }, [initialSelectedUser, initialValues, onClose, resetForm])

  function handleSheetCloseRequest() {
    if (isPending) {
      return
    }
    handleClose()
  }

  async function handleUpdateAssignment() {
    const errors = validateForm()

    if (hasAssignmentFormErrors(errors)) {
      setFieldErrors(errors)
      return
    }

    setFieldErrors({})
    setApiError(null)

    try {
      await updateMutation.mutateAsync({
        assignmentId: assignment.id,
        body: buildChecklistAssignmentUpdatePayload(getFormValues()),
      })
      handleClose()
      onSuccess()
    } catch (error) {
      setApiError(
        resolveChecklistErrorMessage(error, 'L’affectation n’a pas pu être modifiée.'),
      )
    }
  }

  return (
    <TerrainBottomSheet
      title="Modifier l'affectation"
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
            onClick={() => void handleUpdateAssignment()}
          >
            {isPending ? (
              <LoaderCircle className="mr-2 h-4 w-4 animate-spin" aria-hidden />
            ) : null}
            Enregistrer
          </Button>
        </div>
      }
    >
      <ChecklistAssignmentFormFields
        idPrefix="assignment-edit"
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
        intro="Les exécutions à faire seront mises à jour. Les exécutions déjà en cours ou terminées restent conservées."
      />
    </TerrainBottomSheet>
  )
}
