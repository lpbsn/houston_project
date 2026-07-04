import { useState } from 'react'

import { isActionPlanExecutionDetail } from '../lib/action-plan-create-response'
import { buildActionPlanCreateRequest } from '../lib/action-plan-create-payload'
import {
  hasActionPlanCreateFormErrors,
  validateActionPlanCreateForm,
  type ActionPlanCreateFormValues,
} from '../lib/action-plan-form-validation'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import { useCreateActionPlanMutation } from '../hooks'

type UseActionPlanCreateSubmitOptions = {
  establishmentId: string
  canDefineCrossPoleTasks: boolean
  onNavigate: (pathname: string) => void
}

export function useActionPlanCreateSubmit({
  establishmentId,
  canDefineCrossPoleTasks,
  onNavigate,
}: UseActionPlanCreateSubmitOptions) {
  const createMutation = useCreateActionPlanMutation(establishmentId)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [submitError, setSubmitError] = useState<string | null>(null)

  async function submit(values: ActionPlanCreateFormValues) {
    setSubmitError(null)
    const errors = validateActionPlanCreateForm(values, { canDefineCrossPoleTasks })
    setFieldErrors(errors)
    if (hasActionPlanCreateFormErrors(errors)) {
      return false
    }

    try {
      const response = await createMutation.mutateAsync(buildActionPlanCreateRequest(values))
      if (isActionPlanExecutionDetail(response)) {
        onNavigate(`/action-plans/executions/${response.id}`)
      } else {
        onNavigate(`/action-plans/${response.id}`)
      }
      return true
    } catch (error) {
      setSubmitError(
        resolveActionPlanErrorMessage(error, 'Le plan d’action n’a pas pu être créé.'),
      )
      return false
    }
  }

  return {
    submit,
    fieldErrors,
    submitError,
    isSubmitting: createMutation.isPending,
  }
}
