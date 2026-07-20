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
import {
  hasActionPlanCreateFormErrors,
  validateActionPlanCreateForm,
  validateActionPlanCreatePlanningErrors,
  type ActionPlanCreateFormValues,
} from '../lib/action-plan-form-validation'
import type { ActionPlanEventPlanningDraft } from '../lib/action-plan-event-planning-form'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import {
  applyPlanningSubmissionIntent,
  clearPlanningSubmissionIntent,
  resolvePlanningSubmissionIntent,
} from '../lib/action-plan-planning-submission-intent'
import { useCreateActionPlanMutation } from '../hooks'
import type { ActionPlanDetail } from '../types'

const PLANNING_FEEDBACK_STORAGE_KEY = 'houston:planning-feedback'

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
      if (values.saveToLibrary) {
        const response = await createMutation.mutateAsync(buildActionPlanCreateRequest(values))
        if (isActionPlanDetail(response)) {
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
          setSubmitError('Le plan d’action n’a pas pu être créé.')
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
          setSubmitError('Le plan d’action n’a pas pu être créé.')
          return false
        }
        sessionStorage.setItem(
          PLANNING_FEEDBACK_STORAGE_KEY,
          formatPlanningSubmitFeedback(response.summary),
        )
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
      sessionStorage.setItem(
        PLANNING_FEEDBACK_STORAGE_KEY,
        formatPlanningSubmitFeedback({
          executions_created: executionsCreated,
          schedules_created: schedulesCreated,
        }),
      )
      onNavigate('/execution')
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
