import { useCallback, useMemo, useState } from 'react'
import {
  type InfiniteData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import {
  invalidateActionPlanExecutionSurfaces,
  invalidateActionPlanMutationSurfaces,
} from '@/lib/query-invalidation'

import {
  activateActionPlan,
  actionPlansQueryKeys,
  type ActionPlanExecutionFeedCategory,
  type ActionPlanExecutionFeedViewMode,
  cancelActionPlanExecution,
  createActionPlan,
  createObservationFromActionPlanTask,
  deactivateActionPlan,
  deleteActionPlan,
  fetchActionPlanCatalog,
  fetchActionPlanDetail,
  fetchActionPlanExecutionDetail,
  fetchCrossActionPlanExecutionDetail,
  fetchActionPlanExecutionFeed,
  fetchCrossActionPlanExecutionFeed,
  fetchCrossActionPlanExecutionFeedPins,
  fetchActionPlanExecutionUpcoming,
  fetchActionPlanExecutionCalendar,
  fetchCrossActionPlanExecutionCalendar,
  fetchCrossActionPlanExecutionUpcoming,
  markActionPlanExecutionDone,
  markActionPlanTaskDone,
  markActionPlanTaskPending,
  pinActionPlanExecution,
  reopenActionPlanExecution,
  skipActionPlanTask,
  submitActionPlanPlanning,
  unpinActionPlanExecution,
  updateActionPlan,
  updateActionPlanExecution,
  validateActionPlanExecution,
} from './api'
import type {
  ActionPlanCatalogListFilters,
  ActionPlanCreateRequest,
  ActionPlanExecutionDetail,
  ActionPlanExecutionValidateRequest,
  ActionPlanPlanningSubmitRequest,
  ActionPlanTaskCreateObservationRequest,
  ActionPlanTaskExecution,
  ActionPlanTaskSkipRequest,
  PatchedActionPlanExecutionUpdateRequest,
  PatchedActionPlanUpdateRequest,
  ActionPlanExecutionFeedPinsResponse,
  ActionPlanExecutionFeedResponse,
} from './types'
import {
  isActionPlanExecutionDetail,
  isActionPlanPlanningSubmitResponse,
} from './lib/action-plan-create-response'
import {
  applyActionPlanExecutionPinSuccess,
  prepareActionPlanExecutionPinOptimisticUpdate,
  restoreActionPlanExecutionPinOptimisticUpdate,
} from './lib/action-plan-execution-feed-cache'

type ExecutionFeedPageContract = {
  items: unknown[]
  next_cursor: string | null
  has_more: boolean
}

type ExecutionFeedContinuationControls = {
  isRetryingStalledContinuation: boolean
  retryStalledContinuation: () => Promise<void>
}

function useExecutionFeedContinuation<TPage extends ExecutionFeedPageContract>(options: {
  queryKey: readonly unknown[]
  fetchPage: (cursor: string) => Promise<TPage>
}): ExecutionFeedContinuationControls {
  const { fetchPage, queryKey } = options
  const queryClient = useQueryClient()
  const [isRetryingStalledContinuation, setIsRetryingStalledContinuation] = useState(false)

  const retryStalledContinuation = useCallback(async () => {
    const current = queryClient.getQueryData<InfiniteData<TPage, unknown>>(queryKey)
    const lastPageIndex = (current?.pages.length ?? 0) - 1
    const requestCursor = current?.pageParams[lastPageIndex]
    if (!current || lastPageIndex < 1 || typeof requestCursor !== 'string') {
      return
    }
    setIsRetryingStalledContinuation(true)
    try {
      const page = await fetchPage(requestCursor)
      queryClient.setQueryData<InfiniteData<TPage, unknown>>(queryKey, {
        pages: current.pages.map((existing, index) =>
          index === lastPageIndex ? page : existing,
        ),
        pageParams: current.pageParams,
      })
    } catch {
      // Keep the stalled page and its local retry visible.
    } finally {
      setIsRetryingStalledContinuation(false)
    }
  }, [fetchPage, queryClient, queryKey])

  return {
    isRetryingStalledContinuation,
    retryStalledContinuation,
  }
}

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
  options?: { category?: ActionPlanExecutionFeedCategory; source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  const category = options?.category ?? 'all'
  const enabled = source === 'cross' || Boolean(establishmentId)
  const queryKey = useMemo(
    () =>
      source === 'cross'
        ? actionPlansQueryKeys.crossExecutionFeed(viewMode, category)
        : establishmentId
          ? actionPlansQueryKeys.executionFeed(establishmentId, viewMode, category)
          : (['action-plans', 'action-plan-execution-feed', 'none'] as const),
    [category, establishmentId, source, viewMode],
  )
  const fetchPage = useCallback(
    (cursor: string) => {
      if (source === 'cross') {
        return fetchCrossActionPlanExecutionFeed(viewMode, { category, cursor })
      }
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchActionPlanExecutionFeed(establishmentId, viewMode, { category, cursor })
    },
    [category, establishmentId, source, viewMode],
  )
  const query = useInfiniteQuery({
    queryKey,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (source === 'cross') {
        return fetchCrossActionPlanExecutionFeed(viewMode, { category, cursor: pageParam })
      }
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchActionPlanExecutionFeed(establishmentId, viewMode, {
        category,
        cursor: pageParam,
      })
    },
    getNextPageParam: (lastPage, _pages, lastPageParam) => {
      if (
        !lastPage.has_more ||
        !lastPage.next_cursor ||
        lastPage.items.length === 0 ||
        lastPage.next_cursor === lastPageParam
      ) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled,
  })
  const continuation = useExecutionFeedContinuation<ActionPlanExecutionFeedResponse>({
    queryKey,
    fetchPage,
  })
  return { ...query, ...continuation }
}

export function useCrossActionPlanExecutionFeedPinsQuery(
  viewMode: ActionPlanExecutionFeedViewMode,
  category: ActionPlanExecutionFeedCategory,
  options?: { enabled?: boolean },
) {
  const queryKey = useMemo(
    () => actionPlansQueryKeys.crossExecutionFeedPins(viewMode, category),
    [category, viewMode],
  )
  const fetchPage = useCallback(
    (cursor: string) =>
      fetchCrossActionPlanExecutionFeedPins(viewMode, {
        category,
        cursor,
        pageSize: 10,
      }),
    [category, viewMode],
  )
  const query = useInfiniteQuery({
    queryKey,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      fetchCrossActionPlanExecutionFeedPins(viewMode, {
        category,
        cursor: pageParam,
        pageSize: pageParam ? 10 : 3,
      }),
    getNextPageParam: (lastPage, _pages, lastPageParam) => {
      if (
        !lastPage.has_more ||
        !lastPage.next_cursor ||
        lastPage.items.length === 0 ||
        lastPage.next_cursor === lastPageParam
      ) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled: options?.enabled !== false,
  })
  const continuation = useExecutionFeedContinuation<ActionPlanExecutionFeedPinsResponse>({
    queryKey,
    fetchPage,
  })
  return { ...query, ...continuation }
}

export function useActionPlanExecutionUpcomingQuery(
  establishmentId: string | null,
  viewMode: ActionPlanExecutionFeedViewMode,
  options?: {
    source?: 'establishment' | 'cross'
    enabled?: boolean
    pageSize?: number
  },
) {
  const source = options?.source ?? 'establishment'
  const enabled =
    options?.enabled !== false && (source === 'cross' || Boolean(establishmentId))
  const pageSize = options?.pageSize
  return useInfiniteQuery({
    queryKey:
      source === 'cross'
        ? [...actionPlansQueryKeys.crossExecutionUpcoming(viewMode), pageSize ?? 'default']
        : establishmentId
          ? [...actionPlansQueryKeys.executionUpcoming(establishmentId, viewMode), pageSize ?? 'default']
          : ['action-plans', 'action-plan-execution-upcoming', 'none'],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (source === 'cross') {
        return fetchCrossActionPlanExecutionUpcoming(viewMode, {
          cursor: pageParam,
          pageSize,
        })
      }
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchActionPlanExecutionUpcoming(establishmentId, viewMode, {
        cursor: pageParam,
        pageSize,
      })
    },
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more || !lastPage.next_cursor) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled,
  })
}

export function useActionPlanExecutionCalendarQuery(
  establishmentId: string | null,
  viewMode: ActionPlanExecutionFeedViewMode,
  window: { from: string; to: string } | null,
  options?: { enabled?: boolean; source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  const enabled =
    Boolean(window) &&
    options?.enabled !== false &&
    (source === 'cross' || Boolean(establishmentId))
  return useQuery({
    queryKey:
      source === 'cross' && window
        ? actionPlansQueryKeys.crossExecutionCalendar(viewMode, window.from, window.to)
        : establishmentId && window
          ? actionPlansQueryKeys.executionCalendar(
              establishmentId,
              viewMode,
              window.from,
              window.to,
            )
          : ['action-plans', 'action-plan-execution-calendar', 'none'],
    queryFn: () => {
      if (!window) {
        throw new Error('Fenêtre calendrier manquante.')
      }
      if (source === 'cross') {
        return fetchCrossActionPlanExecutionCalendar(viewMode, window)
      }
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchActionPlanExecutionCalendar(establishmentId, viewMode, window)
    },
    enabled,
  })
}

export function useActionPlanExecutionDetailQuery(
  establishmentId: string | null,
  executionId: string | null,
  options?: { source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  return useQuery({
    queryKey:
      source === 'cross' && executionId
        ? actionPlansQueryKeys.crossExecutionDetail(executionId)
        : establishmentId && executionId
          ? actionPlansQueryKeys.executionDetail(establishmentId, executionId)
          : ['action-plans', 'execution-detail', 'none'],
    queryFn: () => {
      if (!executionId) {
        throw new Error('Exécution introuvable.')
      }
      if (source === 'cross') {
        return fetchCrossActionPlanExecutionDetail(executionId)
      }
      if (!establishmentId) {
        throw new Error('Exécution introuvable.')
      }
      return fetchActionPlanExecutionDetail(establishmentId, executionId)
    },
    enabled: Boolean(executionId) && (source === 'cross' || Boolean(establishmentId)),
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
      if (isActionPlanPlanningSubmitResponse(data)) {
        const actionPlanId =
          typeof data.action_plan_id === 'string' ? data.action_plan_id : undefined
        invalidateCatalogSurfaces(queryClient, establishmentId, actionPlanId)
        invalidateActionPlanExecutionSurfaces(queryClient, establishmentId)
        void queryClient.invalidateQueries({
          queryKey: ['action-plans', 'action-plan-execution-feed', establishmentId],
        })
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

export function useUpdateActionPlanExecutionMutation(
  establishmentId: string,
  executionId: string,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: PatchedActionPlanExecutionUpdateRequest) =>
      updateActionPlanExecution(establishmentId, executionId, body),
    onSuccess: () => {
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, executionId)
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

export function deleteActionPlanMutationKey(establishmentId: string, actionPlanId: string) {
  return ['action-plans', 'delete', establishmentId, actionPlanId] as const
}

export function useDeleteActionPlanMutation(establishmentId: string, actionPlanId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: deleteActionPlanMutationKey(establishmentId, actionPlanId),
    mutationFn: () => deleteActionPlan(establishmentId, actionPlanId),
    onSuccess: () => {
      invalidateCatalogSurfaces(queryClient, establishmentId, actionPlanId)
    },
  })
}

export function useSubmitActionPlanPlanningMutation(establishmentId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      actionPlanId,
      body,
    }: {
      actionPlanId: string
      body: ActionPlanPlanningSubmitRequest
    }) => submitActionPlanPlanning(establishmentId, actionPlanId, body),
    onSuccess: (_data, variables) => {
      invalidateCatalogSurfaces(queryClient, establishmentId, variables.actionPlanId)
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId)
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
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ActionPlanExecutionValidateRequest) =>
      validateActionPlanExecution(establishmentId, executionId, body),
    onSuccess: () => {
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, executionId)
    },
  })
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
    mutationFn: async ({
      executionId,
      replaceExecutionId,
    }: {
      executionId: string
      replaceExecutionId?: string
    }) => {
      if (!establishmentId) {
        throw new Error('Plan d’action introuvable.')
      }
      return pinActionPlanExecution(establishmentId, executionId, replaceExecutionId)
    },
    onMutate: async ({ executionId, replaceExecutionId }) => {
      if (!establishmentId || replaceExecutionId) {
        return undefined
      }
      return prepareActionPlanExecutionPinOptimisticUpdate(queryClient, {
        establishmentId,
        executionId,
        isPinned: true,
      })
    },
    onError: (_error, _variables, snapshot) => {
      restoreActionPlanExecutionPinOptimisticUpdate(queryClient, snapshot)
    },
    onSuccess: (result, { executionId, replaceExecutionId }) => {
      if (!establishmentId) {
        return
      }
      applyActionPlanExecutionPinSuccess(queryClient, {
        establishmentId,
        executionId,
        isPinned: result.is_pinned,
        viewMode,
        replacedExecutionId: replaceExecutionId,
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
    onMutate: async (executionId) => {
      if (!establishmentId) {
        return undefined
      }
      return prepareActionPlanExecutionPinOptimisticUpdate(queryClient, {
        establishmentId,
        executionId,
        isPinned: false,
      })
    },
    onError: (_error, _executionId, snapshot) => {
      restoreActionPlanExecutionPinOptimisticUpdate(queryClient, snapshot)
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

function replaceTaskInExecutionDetailCache(
  queryClient: ReturnType<typeof useQueryClient>,
  establishmentId: string,
  executionId: string,
  task: ActionPlanTaskExecution,
) {
  queryClient.setQueryData<ActionPlanExecutionDetail>(
    actionPlansQueryKeys.executionDetail(establishmentId, executionId),
    (current) => {
      if (!current?.task_executions.some((existing) => existing.id === task.id)) {
        return current
      }
      return {
        ...current,
        task_executions: current.task_executions.map((existing) =>
          existing.id === task.id ? task : existing,
        ),
      }
    },
  )
}

export function useMarkActionPlanTaskDoneMutation(
  establishmentId: string,
  executionId: string,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskExecutionId: string) =>
      markActionPlanTaskDone(establishmentId, taskExecutionId),
    onSuccess: (task) => {
      replaceTaskInExecutionDetailCache(queryClient, establishmentId, executionId, task)
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
    onSuccess: (task) => {
      replaceTaskInExecutionDetailCache(queryClient, establishmentId, executionId, task)
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
