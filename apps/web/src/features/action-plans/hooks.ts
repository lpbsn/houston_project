import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  invalidateActionPlanExecutionSurfaces,
  invalidateActionPlanMutationSurfaces,
} from '@/lib/query-invalidation'

import {
  activateActionPlan,
  actionPlansQueryKeys,
  cancelActionPlanExecution,
  createActionPlan,
  createObservationFromActionPlanTask,
  deactivateActionPlan,
  fetchActionPlanCatalog,
  fetchActionPlanDetail,
  fetchActionPlanExecutionDetail,
  launchActionPlanExecution,
  markActionPlanExecutionDone,
  markActionPlanTaskDone,
  reopenActionPlanExecution,
  skipActionPlanTask,
  updateActionPlan,
  validateActionPlanExecution,
} from './api'
import type {
  ActionPlanCatalogListFilters,
  ActionPlanCreateRequest,
  ActionPlanTaskCreateObservationRequest,
  ActionPlanTaskSkipRequest,
  ActionPlanUseRequest,
  PatchedActionPlanUpdateRequest,
} from './types'

function invalidateCatalogSurfaces(
  queryClient: ReturnType<typeof useQueryClient>,
  establishmentId: string,
  actionPlanId?: string,
) {
  invalidateActionPlanMutationSurfaces(queryClient, establishmentId, actionPlanId)
}

export function useActionPlanCatalogQuery(
  establishmentId: string | null,
  filters: ActionPlanCatalogListFilters = {},
) {
  return useQuery({
    queryKey: establishmentId
      ? actionPlansQueryKeys.catalog(establishmentId, filters)
      : ['action-plans', 'catalog', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchActionPlanCatalog(establishmentId, filters)
    },
    enabled: Boolean(establishmentId),
  })
}

export function useActionPlanDetailQuery(
  establishmentId: string | null,
  actionPlanId: string | null,
) {
  return useQuery({
    queryKey:
      establishmentId && actionPlanId
        ? actionPlansQueryKeys.detail(establishmentId, actionPlanId)
        : ['action-plans', 'detail', 'none'],
    queryFn: () => {
      if (!establishmentId || !actionPlanId) {
        throw new Error('Plan d’action introuvable.')
      }
      return fetchActionPlanDetail(establishmentId, actionPlanId)
    },
    enabled: Boolean(establishmentId && actionPlanId),
  })
}

export function useActionPlanExecutionDetailQuery(
  establishmentId: string | null,
  executionId: string | null,
) {
  return useQuery({
    queryKey:
      establishmentId && executionId
        ? actionPlansQueryKeys.executionDetail(establishmentId, executionId)
        : ['action-plans', 'execution-detail', 'none'],
    queryFn: () => {
      if (!establishmentId || !executionId) {
        throw new Error('Exécution introuvable.')
      }
      return fetchActionPlanExecutionDetail(establishmentId, executionId)
    },
    enabled: Boolean(establishmentId && executionId),
  })
}

export function useCreateActionPlanMutation(establishmentId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ActionPlanCreateRequest) => createActionPlan(establishmentId, body),
    onSuccess: () => {
      invalidateCatalogSurfaces(queryClient, establishmentId)
    },
  })
}

export function useUpdateActionPlanMutation(establishmentId: string, actionPlanId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: PatchedActionPlanUpdateRequest) =>
      updateActionPlan(establishmentId, actionPlanId, body),
    onSuccess: () => {
      invalidateCatalogSurfaces(queryClient, establishmentId, actionPlanId)
    },
  })
}

export function useActivateActionPlanMutation(establishmentId: string, actionPlanId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => activateActionPlan(establishmentId, actionPlanId),
    onSuccess: () => {
      invalidateCatalogSurfaces(queryClient, establishmentId, actionPlanId)
    },
  })
}

export function useDeactivateActionPlanMutation(establishmentId: string, actionPlanId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => deactivateActionPlan(establishmentId, actionPlanId),
    onSuccess: () => {
      invalidateCatalogSurfaces(queryClient, establishmentId, actionPlanId)
    },
  })
}

export function useUseActionPlanMutation(establishmentId: string, actionPlanId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ActionPlanUseRequest = { use_shared_chronology: false, assignees: [] }) =>
      launchActionPlanExecution(establishmentId, actionPlanId, body),
    onSuccess: (data) => {
      invalidateCatalogSurfaces(queryClient, establishmentId, actionPlanId)
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, data.id)
    },
  })
}

export function useUseActionPlanFromCatalogMutation(establishmentId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      actionPlanId,
      body = { use_shared_chronology: false, assignees: [] },
    }: {
      actionPlanId: string
      body?: ActionPlanUseRequest
    }) => launchActionPlanExecution(establishmentId, actionPlanId, body),
    onSuccess: (data, variables) => {
      invalidateCatalogSurfaces(queryClient, establishmentId, variables.actionPlanId)
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, data.id)
    },
  })
}

function useExecutionCommandMutation(
  establishmentId: string,
  executionId: string,
  command: (estId: string, execId: string) => Promise<import('./types').ActionPlanExecutionDetail>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => command(establishmentId, executionId),
    onSuccess: () => {
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, executionId)
    },
  })
}

export function useMarkActionPlanExecutionDoneMutation(
  establishmentId: string,
  executionId: string,
) {
  return useExecutionCommandMutation(
    establishmentId,
    executionId,
    markActionPlanExecutionDone,
  )
}

export function useValidateActionPlanExecutionMutation(
  establishmentId: string,
  executionId: string,
) {
  return useExecutionCommandMutation(establishmentId, executionId, validateActionPlanExecution)
}

export function useReopenActionPlanExecutionMutation(
  establishmentId: string,
  executionId: string,
) {
  return useExecutionCommandMutation(establishmentId, executionId, reopenActionPlanExecution)
}

export function useCancelActionPlanExecutionMutation(
  establishmentId: string,
  executionId: string,
) {
  return useExecutionCommandMutation(establishmentId, executionId, cancelActionPlanExecution)
}

export function useMarkActionPlanTaskDoneMutation(
  establishmentId: string,
  executionId: string,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskExecutionId: string) =>
      markActionPlanTaskDone(establishmentId, taskExecutionId),
    onSuccess: () => {
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, executionId)
    },
  })
}

export function useSkipActionPlanTaskMutation(establishmentId: string, executionId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      taskExecutionId,
      body,
    }: {
      taskExecutionId: string
      body?: ActionPlanTaskSkipRequest
    }) => skipActionPlanTask(establishmentId, taskExecutionId, body),
    onSuccess: () => {
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, executionId)
    },
  })
}

export function useCreateObservationFromActionPlanTaskMutation(
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
      body: ActionPlanTaskCreateObservationRequest
    }) => createObservationFromActionPlanTask(establishmentId, taskExecutionId, body),
    onSuccess: () => {
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, executionId)
    },
  })
}
