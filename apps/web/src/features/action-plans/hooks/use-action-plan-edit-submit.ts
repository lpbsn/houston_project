import { useState } from 'react'

import { buildActionPlanUpdateRequest } from '../lib/action-plan-create-payload'
import {
  hasActionPlanCreateFormErrors,
  validateActionPlanCreateForm,
  type ActionPlanCreateFormValues,
} from '../lib/action-plan-form-validation'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
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
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [submitError, setSubmitError] = useState<string | null>(null)

  async function submit(values: ActionPlanCreateFormValues) {
    setSubmitError(null)
    const errors = validateActionPlanCreateForm(values, {
      canDefineCrossPoleTasks,
    })
    setFieldErrors(errors)
    if (hasActionPlanCreateFormErrors(errors)) {
      return false
    }

    try {
      await updateMutation.mutateAsync(buildActionPlanUpdateRequest(values))
      onNavigate(`/action-plans/${actionPlanId}`)
      return true
    } catch (error) {
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
