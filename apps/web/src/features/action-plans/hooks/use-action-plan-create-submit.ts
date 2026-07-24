import { useState } from 'react'

import {
  formatPlanningSubmitFeedback,
  resolveCatalogPlanningSubmit,
} from '../lib/action-plan-catalog-planning-submit'
import {
  isActionPlanExecutionDetail,
  isActionPlanPlanningSubmitResponse,
} from '../lib/action-plan-create-response'
import {
  buildActionPlanCreateRequest,
  buildDirectPlanningCreateRequest,
} from '../lib/action-plan-create-payload'
import { mapActionPlanApiErrors } from '../lib/action-plan-api-error-map'
import {
  clearActionPlanFieldErrorKey,
  listActionPlanPayloadTaskIds,
  mergeActionPlanFieldErrors,
} from '../lib/action-plan-field-errors'
import {
  hasActionPlanCreateFormErrors,
  validateActionPlanCreateForm,
  validateActionPlanCreatePlanningErrors,
  type ActionPlanCreateFormValues,
} from '../lib/action-plan-form-validation'
import type { ActionPlanEventPlanningDraft } from '../lib/action-plan-event-planning-form'
import {
  applyPlanningSubmissionIntent,
  clearPlanningSubmissionIntent,
  resolvePlanningSubmissionIntent,
} from '../lib/action-plan-planning-submission-intent'
import { notifySuccess } from '@/lib/success-toast'

import { useCreateActionPlanMutation } from '../hooks'
import type { ActionPlanDetail } from '../types'

type UseActionPlanCreateSubmitOptions = {
  establishmentId: string
  canDefineCrossPoleTasks: boolean
  staffExecutionMode?: { membershipId: string; pilotBusinessUnitId: string }
  onNavigate: (pathname: string) => void
}

function isActionPlanDetail(data: unknown): data is ActionPlanDetail {
  return (
    typeof data === 'object' &&
    data !== null &&
    'catalog_status' in data &&
    !('replayed' in data) &&
    !('summary' in data)
  )
}

export function useActionPlanCreateSubmit({
  establishmentId,
  canDefineCrossPoleTasks,
  staffExecutionMode,
  onNavigate,
}: UseActionPlanCreateSubmitOptions) {
  const createMutation = useCreateActionPlanMutation(establishmentId)
  const [frontendFieldErrors, setFrontendFieldErrors] = useState<Record<string, string>>({})
  const [apiFieldErrors, setApiFieldErrors] = useState<Record<string, string>>({})
  const [globalError, setGlobalError] = useState<string | null>(null)
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false)
  const [guidanceNonce, setGuidanceNonce] = useState(0)

  function revalidateFrontend(
    values: ActionPlanCreateFormValues,
    planningDraft: ActionPlanEventPlanningDraft,
  ) {
    const errors = validateActionPlanCreateForm(values, {
      canDefineCrossPoleTasks,
      staffExecutionMode,
    })
    const planningErrors = validateActionPlanCreatePlanningErrors(planningDraft, {
      saveToLibrary: values.saveToLibrary,
      staffExecutionMode,
    })
    const merged = { ...errors, ...planningErrors }
    setFrontendFieldErrors(merged)
    return merged
  }

  function clearApiFieldError(key: string) {
    setApiFieldErrors((prev) => clearActionPlanFieldErrorKey(prev, key))
  }

  async function submit(
    values: ActionPlanCreateFormValues,
    planningDraft: ActionPlanEventPlanningDraft,
  ) {
    setGlobalError(null)
    setApiFieldErrors({})
    setHasAttemptedSubmit(true)
    const mergedErrors = revalidateFrontend(values, planningDraft)
    if (hasActionPlanCreateFormErrors(mergedErrors)) {
      setGuidanceNonce((value) => value + 1)
      return false
    }

    try {
      if (values.saveToLibrary) {
        const response = await createMutation.mutateAsync(buildActionPlanCreateRequest(values))
        if (isActionPlanDetail(response)) {
          notifySuccess({
            message: 'Plan ajouté à la bibliothèque.',
            kind: 'created',
          })
          onNavigate(`/action-plans/${response.id}`)
        }
        return true
      }

      // Individual chronology → single atomic POST with planning intent.
      if (planningDraft.usePerAssigneeChronology && !staffExecutionMode) {
        const catalogSubmit = resolveCatalogPlanningSubmit(planningDraft, {
          canSchedule: true,
          staffMode: false,
        })
        if (!catalogSubmit || catalogSubmit.body.items.length === 0) {
          setGlobalError('Le plan d’action n’a pas pu être créé.')
          return false
        }

        const intent = await resolvePlanningSubmissionIntent({
          establishmentId,
          actionPlanId: 'direct-create',
          body: {
            use_shared_chronology: catalogSubmit.body.use_shared_chronology,
            items: catalogSubmit.body.items,
          },
        })
        const stableBody = applyPlanningSubmissionIntent(
          {
            use_shared_chronology: catalogSubmit.body.use_shared_chronology,
            items: catalogSubmit.body.items,
          },
          intent,
        )
        const response = await createMutation.mutateAsync(
          buildDirectPlanningCreateRequest(values, {
            submissionId: stableBody.submission_id,
            useSharedChronology: stableBody.use_shared_chronology,
            items: stableBody.items,
          }),
        )
        clearPlanningSubmissionIntent(establishmentId, 'direct-create')
        if (!isActionPlanPlanningSubmitResponse(response)) {
          setGlobalError('Le plan d’action n’a pas pu être créé.')
          return false
        }
        notifySuccess({
          message: formatPlanningSubmitFeedback(response.summary),
          kind: 'created',
        })
        onNavigate('/execution')
        return true
      }

      const response = await createMutation.mutateAsync(buildActionPlanCreateRequest(values))
      const schedulesCreated = values.schedule.enabled ? 1 : 0
      const executionsCreated = isActionPlanExecutionDetail(response)
        ? 1
        : schedulesCreated > 0
          ? 0
          : 1
      notifySuccess({
        message: formatPlanningSubmitFeedback({
          executions_created: executionsCreated,
          schedules_created: schedulesCreated,
        }),
        kind: 'created',
      })
      onNavigate('/execution')
      return true
    } catch (error) {
      const mapped = mapActionPlanApiErrors(error, {
        payloadTaskIds: listActionPlanPayloadTaskIds(values.tasks),
        taskListKey: 'tasks',
        fallbackDetail: 'Le plan d’action n’a pas pu être créé.',
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
    isSubmitting: createMutation.isPending,
  }
}
