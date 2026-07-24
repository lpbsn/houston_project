import { useCallback, useState } from 'react'

import { notifySuccess } from '@/lib/success-toast'

import { ActionPlansApiError } from '../api'
import { useUpdateActionPlanExecutionMutation } from '../hooks'
import { mapActionPlanApiErrors } from '../lib/action-plan-api-error-map'
import {
  clearActionPlanFieldErrorKey,
  mergeActionPlanFieldErrors,
} from '../lib/action-plan-field-errors'
import {
  buildActionPlanExecutionUpdateRequest,
  hasActionPlanExecutionEditFormErrors,
  isActionPlanExecutionEditConflictError,
  listExecutionPendingPayloadTaskIds,
  validateActionPlanExecutionEditForm,
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
  const [frontendFieldErrors, setFrontendFieldErrors] = useState<Record<string, string>>({})
  const [apiFieldErrors, setApiFieldErrors] = useState<Record<string, string>>({})
  const [globalError, setGlobalError] = useState<string | null>(null)
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false)
  const [guidanceNonce, setGuidanceNonce] = useState(0)

  const revalidateFrontend = useCallback(
    (values: ActionPlanExecutionEditFormValues) => {
      const errors = validateActionPlanExecutionEditForm(values, {
        canDefineCrossPoleTasks,
        staffMode,
        membershipId,
      })
      setFrontendFieldErrors(errors)
      return errors
    },
    [canDefineCrossPoleTasks, membershipId, staffMode],
  )

  function clearApiFieldError(key: string) {
    setApiFieldErrors((prev) => clearActionPlanFieldErrorKey(prev, key))
  }

  async function submit(values: ActionPlanExecutionEditFormValues) {
    setGlobalError(null)
    setHasAttemptedSubmit(true)
    const errors = revalidateFrontend(values)
    if (hasActionPlanExecutionEditFormErrors(errors)) {
      setGuidanceNonce((value) => value + 1)
      return false
    }

    setApiFieldErrors({})
    try {
      await updateMutation.mutateAsync(buildActionPlanExecutionUpdateRequest(values))
      notifySuccess({ message: 'Plan mis à jour.', kind: 'updated' })
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
        setGlobalError(
          error instanceof ActionPlansApiError && error.detail
            ? error.detail
            : 'Ce plan a changé. Les données ont été rechargées.',
        )
        await onConflictReload()
        return false
      }

      const mapped = mapActionPlanApiErrors(error, {
        payloadTaskIds: listExecutionPendingPayloadTaskIds(
          values.pendingTasks,
          values.knownPendingTaskIds,
        ),
        taskListKey: 'pending_tasks',
        fallbackDetail: 'Le plan n’a pas pu être mis à jour.',
      })
      setApiFieldErrors(mapped.apiFieldErrors)
      setGlobalError(mapped.globalError)
      if (Object.keys(mapped.apiFieldErrors).length > 0) {
        setGuidanceNonce((value) => value + 1)
      }
      return false
    }
  }

  return {
    submit,
    frontendFieldErrors,
    setFrontendFieldErrors,
    revalidateFrontend,
    apiFieldErrors,
    clearApiFieldError,
    globalError,
    hasAttemptedSubmit,
    guidanceNonce,
    fieldErrors: mergeActionPlanFieldErrors(frontendFieldErrors, apiFieldErrors),
    submitError: globalError,
    isSubmitting: updateMutation.isPending,
  }
}
