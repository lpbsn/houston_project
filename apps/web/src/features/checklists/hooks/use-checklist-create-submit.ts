import { useCallback, useState } from 'react'

import type { AssignmentFormValues } from '@/features/checklists/lib/checklist-assignment-create-payload'
import { buildChecklistAssignmentCreatePayload } from '@/features/checklists/lib/checklist-assignment-create-payload'
import {
  buildTemplateCreatePayload,
  type ChecklistCreateAssignmentMode,
  type ChecklistCreateFormInput,
} from '@/features/checklists/lib/checklist-create-submit'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import {
  useCreateChecklistAssignmentForTemplateMutation,
  useCreateChecklistTemplateMutation,
} from '@/features/checklists/hooks'

export type ChecklistCreateSubmitInput = ChecklistCreateFormInput & {
  assignmentMode: ChecklistCreateAssignmentMode
  assignmentValues?: AssignmentFormValues
}

type UseChecklistCreateSubmitOptions = {
  establishmentId: string
  onNavigate: (pathname: string, options?: { replace?: boolean }) => void
}

export function useChecklistCreateSubmit({
  establishmentId,
  onNavigate,
}: UseChecklistCreateSubmitOptions) {
  const [createdTemplateId, setCreatedTemplateId] = useState<string | null>(null)
  const [partialFailureMessage, setPartialFailureMessage] = useState<string | null>(null)

  const createTemplateMutation = useCreateChecklistTemplateMutation(establishmentId)
  const createAssignmentMutation = useCreateChecklistAssignmentForTemplateMutation(establishmentId)

  const isSubmitting =
    createTemplateMutation.isPending || createAssignmentMutation.isPending

  const createAssignmentForTemplate = useCallback(
    async (templateId: string, assignmentValues: AssignmentFormValues) => {
      await createAssignmentMutation.mutateAsync({
        templateId,
        body: buildChecklistAssignmentCreatePayload(assignmentValues),
      })
      onNavigate(`/checklists/${templateId}`, { replace: true })
    },
    [createAssignmentMutation, onNavigate],
  )

  const submit = useCallback(
    async (input: ChecklistCreateSubmitInput) => {
      setPartialFailureMessage(null)

      if (
        createdTemplateId &&
        input.assignmentMode === 'create_now' &&
        input.assignmentValues
      ) {
        try {
          await createAssignmentForTemplate(createdTemplateId, input.assignmentValues)
          setCreatedTemplateId(null)
        } catch (error) {
          setPartialFailureMessage(
            resolveChecklistErrorMessage(error, 'L’affectation n’a pas pu être créée.'),
          )
          throw new Error('La checklist a été créée, mais l’affectation a échoué.', {
            cause: error,
          })
        }
        return
      }

      let templateId = createdTemplateId

      if (!templateId) {
        try {
          const template = await createTemplateMutation.mutateAsync(
            buildTemplateCreatePayload(input),
          )
          templateId = template.id
        } catch (error) {
          throw new Error(
            resolveChecklistErrorMessage(error, 'La checklist n’a pas pu être créée.'),
            { cause: error },
          )
        }
      }

      if (input.assignmentMode === 'create_now' && input.assignmentValues) {
        try {
          await createAssignmentForTemplate(templateId, input.assignmentValues)
          setCreatedTemplateId(null)
        } catch (error) {
          setCreatedTemplateId(templateId)
          setPartialFailureMessage(
            resolveChecklistErrorMessage(error, 'L’affectation n’a pas pu être créée.'),
          )
          throw new Error('La checklist a été créée, mais l’affectation a échoué.', {
            cause: error,
          })
        }
        return
      }

      setCreatedTemplateId(null)
      onNavigate(`/checklists/${templateId}`, { replace: true })
    },
    [
      createAssignmentForTemplate,
      createTemplateMutation,
      createdTemplateId,
      onNavigate,
    ],
  )

  return {
    submit,
    createdTemplateId,
    partialFailureMessage,
    isSubmitting,
    clearPartialFailure: () => setPartialFailureMessage(null),
  }
}
