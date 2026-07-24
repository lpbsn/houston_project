import { useState } from 'react'

import { buildActionPlanUpdateRequest } from '../lib/action-plan-create-payload'
import { mapActionPlanApiErrors } from '../lib/action-plan-api-error-map'
import {
  clearActionPlanFieldErrorKey,
  listActionPlanPayloadTaskIds,
  mergeActionPlanFieldErrors,
} from '../lib/action-plan-field-errors'
import {
  hasActionPlanCreateFormErrors,
  validateActionPlanCreateForm,
  type ActionPlanCreateFormValues,
} from '../lib/action-plan-form-validation'
import { notifySuccess } from '@/lib/success-toast'

import { useUpdateActionPlanMutation } from '../hooks'

type UseActionPlanEditSubmitOptions = {
  establishmentId: string
  actionPlanId: string
  canDefineCrossPoleTasks: boolean
  onNavigate: (pathname: string) => void
}

export function useActionPlanEditSubmit({
  establishmentId,
  actionPlanId,
  canDefineCrossPoleTasks,
  onNavigate,
}: UseActionPlanEditSubmitOptions) {
  const updateMutation = useUpdateActionPlanMutation(establishmentId, actionPlanId)
  const [frontendFieldErrors, setFrontendFieldErrors] = useState<Record<string, string>>({})
  const [apiFieldErrors, setApiFieldErrors] = useState<Record<string, string>>({})
  const [globalError, setGlobalError] = useState<string | null>(null)
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false)
  const [guidanceNonce, setGuidanceNonce] = useState(0)

  function revalidateFrontend(values: ActionPlanCreateFormValues) {
    const errors = validateActionPlanCreateForm(values, {
      canDefineCrossPoleTasks,
    })
    setFrontendFieldErrors(errors)
    return errors
  }

  function clearApiFieldError(key: string) {
    setApiFieldErrors((prev) => clearActionPlanFieldErrorKey(prev, key))
  }

  async function submit(values: ActionPlanCreateFormValues) {
    setGlobalError(null)
    setHasAttemptedSubmit(true)
    const errors = revalidateFrontend(values)
    if (hasActionPlanCreateFormErrors(errors)) {
      setGuidanceNonce((value) => value + 1)
      return false
    }

    setApiFieldErrors({})
    try {
      await updateMutation.mutateAsync(buildActionPlanUpdateRequest(values))
      notifySuccess({ message: 'Plan mis à jour.', kind: 'updated' })
      onNavigate(`/action-plans/${actionPlanId}`)
      return true
    } catch (error) {
      const mapped = mapActionPlanApiErrors(error, {
        payloadTaskIds: listActionPlanPayloadTaskIds(values.tasks),
        taskListKey: 'tasks',
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
