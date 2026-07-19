import { useState } from 'react'

import { ActionPlansApiError } from '../api'
import { useUpdateActionPlanExecutionMutation } from '../hooks'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import {
  buildActionPlanExecutionUpdateRequest,
  hasActionPlanExecutionEditFormErrors,
  isActionPlanExecutionEditConflictError,
  validateActionPlanExecutionEditForm,
  type ActionPlanExecutionEditFormErrors,
  type ActionPlanExecutionEditFormValues,
} from '../lib/action-plan-execution-edit-form'

type UseActionPlanExecutionEditSubmitOptions = {
  establishmentId: string
  executionId: string
  canDefineCrossPoleTasks: boolean
  staffMode: boolean
  membershipId?: string
  onNavigate: (pathname: string) => void
  onConflictReload: () => Promise<void>
}

export function useActionPlanExecutionEditSubmit({
  establishmentId,
  executionId,
  canDefineCrossPoleTasks,
  staffMode,
  membershipId,
  onNavigate,
  onConflictReload,
}: UseActionPlanExecutionEditSubmitOptions) {
  const updateMutation = useUpdateActionPlanExecutionMutation(establishmentId, executionId)
  const [fieldErrors, setFieldErrors] = useState<ActionPlanExecutionEditFormErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)

  async function submit(values: ActionPlanExecutionEditFormValues) {
    setSubmitError(null)
    const errors = validateActionPlanExecutionEditForm(values, {
      canDefineCrossPoleTasks,
      staffMode,
      membershipId,
    })
    setFieldErrors(errors)
    if (hasActionPlanExecutionEditFormErrors(errors)) {
      return false
    }

    try {
      await updateMutation.mutateAsync(buildActionPlanExecutionUpdateRequest(values))
      onNavigate(`/action-plans/executions/${executionId}`)
      return true
    } catch (error) {
      const apiError =
        error instanceof ActionPlansApiError
          ? error
          : error instanceof Error
            ? { status: undefined, code: null, detail: error.message }
            : { status: undefined, code: null, detail: '' }

      if (isActionPlanExecutionEditConflictError(apiError)) {
        setSubmitError(
          resolveActionPlanErrorMessage(
            error,
            'Ce plan a changé. Les données ont été rechargées.',
          ),
        )
        await onConflictReload()
        return false
      }

      setSubmitError(
        resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être mis à jour.'),
      )
      return false
    }
  }

  return {
    submit,
    fieldErrors,
    submitError,
    isSubmitting: updateMutation.isPending,
  }
}
