import { useState } from 'react'

import { isActionPlanExecutionDetail } from '../lib/action-plan-create-response'
import { buildActionPlanCreateRequest, buildActionPlanShellCreateRequest } from '../lib/action-plan-create-payload'
import {
  hasActionPlanCreateFormErrors,
  validateActionPlanCreateForm,
  validateActionPlanCreatePlanningErrors,
  type ActionPlanCreateFormValues,
} from '../lib/action-plan-form-validation'
import type { ActionPlanEventPlanningDraft } from '../lib/action-plan-event-planning-form'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import { useCreateActionPlanMutation } from '../hooks'

type UseActionPlanCreateSubmitOptions = {
  establishmentId: string
  canDefineCrossPoleTasks: boolean
  staffExecutionMode?: { membershipId: string; pilotBusinessUnitId: string }
  onNavigate: (pathname: string) => void
}

export function useActionPlanCreateSubmit({
  establishmentId,
  canDefineCrossPoleTasks,
  staffExecutionMode,
  onNavigate,
}: UseActionPlanCreateSubmitOptions) {
  const createMutation = useCreateActionPlanMutation(establishmentId)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [submitError, setSubmitError] = useState<string | null>(null)

  async function submit(
    values: ActionPlanCreateFormValues,
    planningDraft: ActionPlanEventPlanningDraft,
  ) {
    setSubmitError(null)
    const errors = validateActionPlanCreateForm(values, {
      canDefineCrossPoleTasks,
      staffExecutionMode,
    })
    const planningErrors = validateActionPlanCreatePlanningErrors(planningDraft, {
      saveToLibrary: values.saveToLibrary,
      staffExecutionMode,
    })
    const mergedErrors = { ...errors, ...planningErrors }
    setFieldErrors(mergedErrors)
    if (hasActionPlanCreateFormErrors(mergedErrors)) {
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

  async function submitShell(
    values: ActionPlanCreateFormValues,
    options: {
      reusableForScheduling?: boolean
      planningDraft?: ActionPlanEventPlanningDraft
    } = {},
  ) {
    setSubmitError(null)
    const errors = validateActionPlanCreateForm(values, {
      canDefineCrossPoleTasks,
      staffExecutionMode,
    })
    const planningErrors = options.planningDraft
      ? validateActionPlanCreatePlanningErrors(options.planningDraft, {
          saveToLibrary: values.saveToLibrary,
          staffExecutionMode,
        })
      : {}
    const mergedErrors = { ...errors, ...planningErrors }
    setFieldErrors(mergedErrors)
    if (hasActionPlanCreateFormErrors(mergedErrors)) {
      return null
    }

    try {
      return await createMutation.mutateAsync(
        buildActionPlanShellCreateRequest(values, options),
      )
    } catch (error) {
      setSubmitError(
        resolveActionPlanErrorMessage(error, 'Le plan d’action n’a pas pu être créé.'),
      )
      return null
    }
  }

  return {
    submit,
    submitShell,
    fieldErrors,
    submitError,
    isSubmitting: createMutation.isPending,
  }
}
