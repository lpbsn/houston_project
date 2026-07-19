import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  invalidateActionPlanExecutionSurfaces,
  invalidateActionPlanMutationSurfaces,
} from '@/lib/query-invalidation'

import {
  activateActionPlan,
  actionPlansQueryKeys,
  type ActionPlanExecutionFeedViewMode,
  cancelActionPlanExecution,
  createActionPlan,
  createActionPlanSchedule,
  createObservationFromActionPlanTask,
  deactivateActionPlan,
  fetchActionPlanCatalog,
  fetchActionPlanDetail,
  fetchActionPlanExecutionDetail,
  fetchActionPlanExecutionFeed,
  fetchActionPlanExecutionUpcoming,
  launchActionPlanExecution,
  markActionPlanExecutionDone,
  markActionPlanTaskDone,
  markActionPlanTaskPending,
  pinActionPlanExecution,
  reopenActionPlanExecution,
  skipActionPlanTask,
  submitMixedActionPlanCatalog,
  unpinActionPlanExecution,
  updateActionPlan,
  validateActionPlanExecution,
} from './api'
import type {
  ActionPlanCatalogListFilters,
  ActionPlanCreateRequest,
  ActionPlanScheduleCreateRequest,
  ActionPlanMixedSubmitRequest,
  ActionPlanTaskCreateObservationRequest,
  ActionPlanTaskSkipRequest,
  ActionPlanUseRequest,
  PatchedActionPlanUpdateRequest,
} from './types'
import { isActionPlanExecutionDetail } from './lib/action-plan-create-response'
import { applyActionPlanExecutionPinSuccess } from './lib/action-plan-execution-feed-cache'

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

export function useActionPlanExecutionFeedQuery(
  establishmentId: string | null,
  viewMode: ActionPlanExecutionFeedViewMode,
) {
  return useInfiniteQuery({
    queryKey: establishmentId
      ? actionPlansQueryKeys.executionFeed(establishmentId, viewMode)
      : ['action-plans', 'action-plan-execution-feed', 'none'],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchActionPlanExecutionFeed(establishmentId, viewMode, {
        cursor: pageParam,
      })
    },
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more || !lastPage.next_cursor) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled: Boolean(establishmentId),
  })
}

export function useActionPlanExecutionUpcomingQuery(
  establishmentId: string | null,
  viewMode: ActionPlanExecutionFeedViewMode,
) {
  return useInfiniteQuery({
    queryKey: establishmentId
      ? actionPlansQueryKeys.executionUpcoming(establishmentId, viewMode)
      : ['action-plans', 'action-plan-execution-upcoming', 'none'],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchActionPlanExecutionUpcoming(establishmentId, viewMode, {
        cursor: pageParam,
      })
    },
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more || !lastPage.next_cursor) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled: Boolean(establishmentId),
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
    onSuccess: (data) => {
      if (isActionPlanExecutionDetail(data)) {
        invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, data.id)
        return
      }
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

export function useCreateActionPlanScheduleMutation(
  establishmentId: string,
  actionPlanId: string,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ActionPlanScheduleCreateRequest) =>
      createActionPlanSchedule(establishmentId, actionPlanId, body),
    onSuccess: () => {
      invalidateCatalogSurfaces(queryClient, establishmentId, actionPlanId)
      void queryClient.invalidateQueries({
        queryKey: ['action-plans', 'action-plan-execution-feed', establishmentId],
      })
    },
  })
}

export function useScheduleActionPlanFromCatalogMutation(establishmentId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      actionPlanId,
      body,
    }: {
      actionPlanId: string
      body: ActionPlanScheduleCreateRequest
    }) => createActionPlanSchedule(establishmentId, actionPlanId, body),
    onSuccess: (_data, variables) => {
      invalidateCatalogSurfaces(queryClient, establishmentId, variables.actionPlanId)
      void queryClient.invalidateQueries({
        queryKey: ['action-plans', 'action-plan-execution-feed', establishmentId],
      })
    },
  })
}

export function useSubmitMixedActionPlanFromCatalogMutation(establishmentId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      actionPlanId,
      body,
    }: {
      actionPlanId: string
      body: ActionPlanMixedSubmitRequest
    }) => submitMixedActionPlanCatalog(establishmentId, actionPlanId, body),
    onSuccess: (data, variables) => {
      invalidateCatalogSurfaces(queryClient, establishmentId, variables.actionPlanId)
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, data.execution.id)
      void queryClient.invalidateQueries({
        queryKey: ['action-plans', 'action-plan-execution-feed', establishmentId],
      })
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

export function usePinActionPlanExecutionMutation(
  establishmentId: string | null,
  viewMode: ActionPlanExecutionFeedViewMode,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (executionId: string) => {
      if (!establishmentId) {
        throw new Error('Plan d’action introuvable.')
      }
      return pinActionPlanExecution(establishmentId, executionId)
    },
    onSuccess: (result, executionId) => {
      if (!establishmentId) {
        return
      }
      applyActionPlanExecutionPinSuccess(queryClient, {
        establishmentId,
        executionId,
        isPinned: result.is_pinned,
        viewMode,
      })
    },
  })
}

export function useUnpinActionPlanExecutionMutation(
  establishmentId: string | null,
  viewMode: ActionPlanExecutionFeedViewMode,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (executionId: string) => {
      if (!establishmentId) {
        throw new Error('Plan d’action introuvable.')
      }
      return unpinActionPlanExecution(establishmentId, executionId)
    },
    onSuccess: (result, executionId) => {
      if (!establishmentId) {
        return
      }
      applyActionPlanExecutionPinSuccess(queryClient, {
        establishmentId,
        executionId,
        isPinned: result.is_pinned,
        viewMode,
      })
    },
  })
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

export function useMarkActionPlanTaskPendingMutation(
  establishmentId: string,
  executionId: string,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskExecutionId: string) =>
      markActionPlanTaskPending(establishmentId, taskExecutionId),
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
