import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  invalidateChecklistMutationSurfaces,
} from '@/lib/query-invalidation'

import {
  activateChecklistTemplate,
  cancelChecklistExecution,
  checklistsQueryKeys,
  createChecklistAssignment,
  createChecklistTask,
  createChecklistTaskObservation,
  createChecklistTemplate,
  createExecutionFromTemplate,
  createRegisteredChecklistTemplate,
  deactivateChecklistAssignment,
  deactivateChecklistTemplate,
  deleteChecklistTask,
  deleteChecklistTemplate,
  fetchChecklistAssignments,
  fetchChecklistExecutionDetail,
  fetchChecklistTemplateDetail,
  fetchChecklistTemplates,
  markChecklistTaskDone,
  reorderChecklistTasks,
  type RegisteredChecklistTemplateInput,
  skipChecklistTask,
  updateChecklistAssignment,
  updateChecklistTask,
  updateChecklistTemplate,
} from './api'
import type {
  ChecklistAssignmentCreateRequest,
  ChecklistTemplateExecutionCreateRequest,
  ChecklistTemplateListFilters,
  PatchedChecklistAssignmentUpdateRequest,
  ChecklistTaskCreateObservationRequest,
  ChecklistTaskReorderRequest,
  ChecklistTaskSkipRequest,
  ChecklistTaskTemplateCreateRequest,
  ChecklistTemplateCreateRequest,
  PatchedChecklistTaskTemplateUpdateRequest,
  PatchedChecklistTemplateUpdateRequest,
} from './types'

function invalidateChecklistSurfaces(
  queryClient: ReturnType<typeof useQueryClient>,
  establishmentId: string,
  templateId?: string,
) {
  invalidateChecklistMutationSurfaces(queryClient, establishmentId, templateId)
}

function invalidateChecklistExecutionSurfaces(
  queryClient: ReturnType<typeof useQueryClient>,
  establishmentId: string,
  executionId: string,
) {
  void queryClient.invalidateQueries({
    queryKey: checklistsQueryKeys.executionDetail(establishmentId, executionId),
  })
  invalidateChecklistMutationSurfaces(queryClient, establishmentId)
}

export function useChecklistTemplatesQuery(
  establishmentId: string | null,
  filters: ChecklistTemplateListFilters = {},
) {
  return useQuery({
    queryKey: establishmentId
      ? checklistsQueryKeys.templates(establishmentId, filters)
      : ['checklists', 'templates', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchChecklistTemplates(establishmentId, filters)
    },
    enabled: Boolean(establishmentId),
  })
}

export function useChecklistTemplateDetailQuery(
  establishmentId: string | null,
  templateId: string | null,
) {
  return useQuery({
    queryKey:
      establishmentId && templateId
        ? checklistsQueryKeys.templateDetail(establishmentId, templateId)
        : ['checklists', 'template-detail', 'none'],
    queryFn: () => {
      if (!establishmentId || !templateId) {
        throw new Error('Checklist introuvable.')
      }
      return fetchChecklistTemplateDetail(establishmentId, templateId)
    },
    enabled: Boolean(establishmentId && templateId),
  })
}

export function useChecklistAssignmentsQuery(establishmentId: string | null) {
  return useQuery({
    queryKey: establishmentId
      ? checklistsQueryKeys.assignments(establishmentId)
      : ['checklists', 'assignments', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchChecklistAssignments(establishmentId)
    },
    enabled: Boolean(establishmentId),
  })
}

export function useCreateChecklistTemplateMutation(establishmentId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: ChecklistTemplateCreateRequest) =>
      createChecklistTemplate(establishmentId, body),
    onSuccess: (data) => {
      invalidateChecklistSurfaces(queryClient, establishmentId, data.id)
    },
  })
}

export function useCreateRegisteredChecklistTemplateMutation(establishmentId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: RegisteredChecklistTemplateInput) =>
      createRegisteredChecklistTemplate(establishmentId, input),
    onSuccess: (data) => {
      invalidateChecklistSurfaces(queryClient, establishmentId, data.id)
    },
  })
}

export function useUpdateChecklistTemplateMutation(
  establishmentId: string,
  templateId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: PatchedChecklistTemplateUpdateRequest) =>
      updateChecklistTemplate(establishmentId, templateId, body),
    onSuccess: () => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useActivateChecklistTemplateMutation(
  establishmentId: string,
  templateId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => activateChecklistTemplate(establishmentId, templateId),
    onSuccess: () => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useDeactivateChecklistTemplateMutation(
  establishmentId: string,
  templateId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => deactivateChecklistTemplate(establishmentId, templateId),
    onSuccess: () => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useDeleteChecklistTemplateMutation(establishmentId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (templateId: string) =>
      deleteChecklistTemplate(establishmentId, templateId),
    onSuccess: (_data, templateId) => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useCreateChecklistTaskMutation(establishmentId: string, templateId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: ChecklistTaskTemplateCreateRequest) =>
      createChecklistTask(establishmentId, templateId, body),
    onSuccess: () => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useUpdateChecklistTaskMutation(establishmentId: string, templateId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      taskTemplateId,
      body,
    }: {
      taskTemplateId: string
      body: PatchedChecklistTaskTemplateUpdateRequest
    }) => updateChecklistTask(establishmentId, taskTemplateId, body),
    onSuccess: () => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useDeleteChecklistTaskMutation(establishmentId: string, templateId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (taskTemplateId: string) =>
      deleteChecklistTask(establishmentId, taskTemplateId),
    onSuccess: () => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useReorderChecklistTasksMutation(establishmentId: string, templateId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: ChecklistTaskReorderRequest) =>
      reorderChecklistTasks(establishmentId, templateId, body),
    onSuccess: () => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useCreateChecklistAssignmentMutation(
  establishmentId: string,
  templateId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: ChecklistAssignmentCreateRequest) =>
      createChecklistAssignment(establishmentId, templateId, body),
    onSuccess: () => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useCreateChecklistAssignmentForTemplateMutation(establishmentId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      templateId,
      body,
    }: {
      templateId: string
      body: ChecklistAssignmentCreateRequest
    }) => createChecklistAssignment(establishmentId, templateId, body),
    onSuccess: (_data, variables) => {
      invalidateChecklistSurfaces(queryClient, establishmentId, variables.templateId)
    },
  })
}

export function useUpdateChecklistAssignmentMutation(
  establishmentId: string,
  templateId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      assignmentId,
      body,
    }: {
      assignmentId: string
      body: PatchedChecklistAssignmentUpdateRequest
    }) => updateChecklistAssignment(establishmentId, assignmentId, body),
    onSuccess: () => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useDeactivateChecklistAssignmentMutation(
  establishmentId: string,
  templateId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (assignmentId: string) =>
      deactivateChecklistAssignment(establishmentId, assignmentId),
    onSuccess: () => {
      invalidateChecklistSurfaces(queryClient, establishmentId, templateId)
    },
  })
}

export function useCreateTemplateExecutionMutation(
  establishmentId: string,
  templateId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: ChecklistTemplateExecutionCreateRequest) =>
      createExecutionFromTemplate(establishmentId, templateId, body),
    onSuccess: (data) => {
      invalidateChecklistExecutionSurfaces(queryClient, establishmentId, data.id)
    },
  })
}

export function useChecklistExecutionDetailQuery(
  establishmentId: string | null,
  executionId: string | null,
) {
  return useQuery({
    queryKey:
      establishmentId && executionId
        ? checklistsQueryKeys.executionDetail(establishmentId, executionId)
        : ['checklists', 'execution-detail', 'none'],
    queryFn: () => {
      if (!establishmentId || !executionId) {
        throw new Error('Exécution introuvable.')
      }
      return fetchChecklistExecutionDetail(establishmentId, executionId)
    },
    enabled: Boolean(establishmentId && executionId),
  })
}

export function useCancelChecklistExecutionMutation(
  establishmentId: string,
  executionId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => cancelChecklistExecution(establishmentId, executionId),
    onSuccess: () => {
      invalidateChecklistExecutionSurfaces(queryClient, establishmentId, executionId)
    },
  })
}

export function useMarkChecklistTaskDoneMutation(
  establishmentId: string,
  executionId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (taskExecutionId: string) =>
      markChecklistTaskDone(establishmentId, taskExecutionId),
    onSuccess: () => {
      invalidateChecklistExecutionSurfaces(queryClient, establishmentId, executionId)
    },
  })
}

export function useSkipChecklistTaskMutation(establishmentId: string, executionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      taskExecutionId,
      body,
    }: {
      taskExecutionId: string
      body?: ChecklistTaskSkipRequest
    }) => skipChecklistTask(establishmentId, taskExecutionId, body),
    onSuccess: () => {
      invalidateChecklistExecutionSurfaces(queryClient, establishmentId, executionId)
    },
  })
}

export function useCreateChecklistTaskObservationMutation(
  establishmentId: string,
  executionId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      taskExecutionId,
      body,
    }: {
      taskExecutionId: string
      body: ChecklistTaskCreateObservationRequest
    }) => createChecklistTaskObservation(establishmentId, taskExecutionId, body),
    onSuccess: () => {
      invalidateChecklistExecutionSurfaces(queryClient, establishmentId, executionId)
    },
  })
}
