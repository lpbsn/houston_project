import { useCallback, useMemo, useRef, useState } from 'react'
import {
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
  clearClientSubmissionId,
  clientSubmissionIdForFingerprint,
  type ClientSubmissionSlot,
} from '@/features/observations/lib/observation-compose-submit'

import {
  activateActionPlan,
  actionPlansQueryKeys,
  type ActionPlanExecutionFeedCategory,
  type ActionPlanExecutionFeedViewMode,
  ActionPlansApiError,
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
} from './types'
import {
  isActionPlanExecutionDetail,
  isActionPlanPlanningSubmitResponse,
} from './lib/action-plan-create-response'
import {
  placeResumePage,
  prependBehindPage,
  showRetainedPageOne,
  windowHead,
} from '@/lib/feed-reading-window'

import {
  appendExecutionFeedWindow,
  applyActionPlanExecutionPinSuccess,
  executionFeedCacheFromPage,
  executionPinsCacheFromPage,
  prepareActionPlanExecutionPinOptimisticUpdate,
  restoreActionPlanExecutionPinOptimisticUpdate,
  type ExecutionFeedCacheState,
  type ExecutionPinsCacheState,
} from './lib/action-plan-execution-feed-cache'

class StaleExecutionFeedRefresh extends Error {
  constructor() {
    super('stale execution feed refresh')
    this.name = 'StaleExecutionFeedRefresh'
  }
}

export function isStaleExecutionFeedRefresh(error: unknown): boolean {
  return error instanceof StaleExecutionFeedRefresh
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
  const queryClient = useQueryClient()
  const refreshEpoch = useRef(0)
  const continuationEpoch = useRef(0)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [continuationError, setContinuationError] = useState<unknown>(null)
  const [refreshError, setRefreshError] = useState<unknown>(null)
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
    (cursor?: string) => {
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
  const query = useQuery({
    queryKey,
    queryFn: async () => {
      const page = await fetchPage()
      const previous = queryClient.getQueryData<ExecutionFeedCacheState>(queryKey)
      const generation = (previous?.window.generation ?? 0) + 1
      return executionFeedCacheFromPage(page, generation)
    },
    enabled,
  })

  const loadMore = useCallback(async () => {
    const current = queryClient.getQueryData<ExecutionFeedCacheState>(queryKey)
    const head = current ? windowHead(current.window) : null
    if (!current || !head?.hasMore || !head.nextCursor || current.window.stalled) {
      return
    }
    const generation = current.window.generation
    const requestedCursor = head.nextCursor
    const ticket = ++continuationEpoch.current
    setIsLoadingMore(true)
    setContinuationError(null)
    try {
      const page = await fetchPage(requestedCursor)
      if (ticket !== continuationEpoch.current) {
        return
      }
      const latest = queryClient.getQueryData<ExecutionFeedCacheState>(queryKey)
      if (!latest || latest.window.generation !== generation) {
        return
      }
      const appended = appendExecutionFeedWindow(latest.window, page, requestedCursor)
      queryClient.setQueryData<ExecutionFeedCacheState>(queryKey, {
        ...latest,
        window: appended.window,
      })
      if (appended.stalled) {
        setContinuationError(new Error('La suite du feed n’a pas pu être chargée.'))
      }
    } catch (error) {
      if (ticket === continuationEpoch.current) {
        setContinuationError(error)
      }
    } finally {
      if (ticket === continuationEpoch.current) {
        setIsLoadingMore(false)
      }
    }
  }, [fetchPage, queryClient, queryKey])

  const refresh = useCallback(async () => {
    const ticket = ++refreshEpoch.current
    continuationEpoch.current += 1
    setIsRefreshing(true)
    setRefreshError(null)
    try {
      const page = await fetchPage()
      if (ticket !== refreshEpoch.current) {
        throw new StaleExecutionFeedRefresh()
      }
      const previous = queryClient.getQueryData<ExecutionFeedCacheState>(queryKey)
      queryClient.setQueryData(
        queryKey,
        executionFeedCacheFromPage(page, (previous?.window.generation ?? 0) + 1),
      )
      setContinuationError(null)
      return true
    } catch (error) {
      if (ticket === refreshEpoch.current && !isStaleExecutionFeedRefresh(error)) {
        setRefreshError(error)
      }
      return false
    } finally {
      if (ticket === refreshEpoch.current) {
        setIsRefreshing(false)
      }
    }
  }, [fetchPage, queryClient, queryKey])

  const resumeAt = useCallback(
    async (cursor: string) => {
      const current = queryClient.getQueryData<ExecutionFeedCacheState>(queryKey)
      if (!current) {
        return
      }
      const generation = current.window.generation
      const page = await fetchPage(cursor)
      const latest = queryClient.getQueryData<ExecutionFeedCacheState>(queryKey)
      if (!latest || latest.window.generation !== generation) {
        return
      }
      queryClient.setQueryData<ExecutionFeedCacheState>(queryKey, {
        ...latest,
        window: placeResumePage(latest.window, {
          requestCursor: cursor,
          nextCursor: page.next_cursor,
          hasMore: page.has_more,
          items: page.items,
        }),
      })
    },
    [fetchPage, queryClient, queryKey],
  )

  const showPageOne = useCallback(() => {
    queryClient.setQueryData<ExecutionFeedCacheState>(queryKey, (current) =>
      current ? { ...current, window: showRetainedPageOne(current.window) } : current,
    )
  }, [queryClient, queryKey])

  const loadBehind = useCallback(async () => {
    const current = queryClient.getQueryData<ExecutionFeedCacheState>(queryKey)
    if (!current?.window.behindCursor) {
      return
    }
    const cursor = current.window.behindCursor
    const generation = current.window.generation
    const ticket = ++continuationEpoch.current
    setIsLoadingMore(true)
    setContinuationError(null)
    try {
      const page = await fetchPage(cursor)
      if (ticket !== continuationEpoch.current) {
        return
      }
      const latest = queryClient.getQueryData<ExecutionFeedCacheState>(queryKey)
      if (!latest || latest.window.generation !== generation || latest.window.behindCursor !== cursor) {
        return
      }
      const restored = prependBehindPage(latest.window, {
        items: page.items,
        nextCursor: page.next_cursor,
        hasMore: page.has_more,
      }, (wrapper) => wrapper.action_plan_execution.id)
      queryClient.setQueryData<ExecutionFeedCacheState>(queryKey, {
        ...latest,
        window: restored.window,
      })
      if (restored.stalled) {
        setContinuationError(new Error('La suite du feed n’a pas pu être chargée.'))
      }
    } catch (error) {
      if (ticket === continuationEpoch.current) {
        setContinuationError(error)
      }
    } finally {
      if (ticket === continuationEpoch.current) {
        setIsLoadingMore(false)
      }
    }
  }, [fetchPage, queryClient, queryKey])

  const retryStalledContinuation = useCallback(async () => {
    if (
      continuationError instanceof ActionPlansApiError &&
      continuationError.code === 'cursor_context_mismatch'
    ) {
      await refresh()
      return
    }
    queryClient.setQueryData<ExecutionFeedCacheState>(queryKey, (current) =>
      current ? { ...current, window: { ...current.window, stalled: false } } : current,
    )
    setContinuationError(null)
    await loadMore()
  }, [continuationError, loadMore, queryClient, queryKey, refresh])

  const head = query.data ? windowHead(query.data.window) : null
  return {
    ...query,
    hasNextPage: Boolean(head?.hasMore) && !query.data?.window.stalled,
    isFetchingNextPage: isLoadingMore,
    fetchNextPage: loadMore,
    loadMore,
    isLoadingMore,
    continuationError,
    refresh,
    isRefreshing,
    refreshError,
    isRetryingStalledContinuation: isLoadingMore,
    retryStalledContinuation,
    showPageOne,
    loadBehind,
    resumeAt,
  }
}

export function useCrossActionPlanExecutionFeedPinsQuery(
  viewMode: ActionPlanExecutionFeedViewMode,
  category: ActionPlanExecutionFeedCategory,
  options?: { enabled?: boolean },
) {
  const queryClient = useQueryClient()
  const continuationEpoch = useRef(0)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [continuationError, setContinuationError] = useState<unknown>(null)
  const queryKey = useMemo(
    () => actionPlansQueryKeys.crossExecutionFeedPins(viewMode, category),
    [category, viewMode],
  )
  const query = useQuery({
    queryKey,
    queryFn: async () => {
      const page = await fetchCrossActionPlanExecutionFeedPins(viewMode, {
        category,
        pageSize: 3,
      })
      const previous = queryClient.getQueryData<ExecutionPinsCacheState>(queryKey)
      return executionPinsCacheFromPage(page, (previous?.window.generation ?? 0) + 1)
    },
    enabled: options?.enabled !== false,
  })
  const loadMore = useCallback(async () => {
    const current = queryClient.getQueryData<ExecutionPinsCacheState>(queryKey)
    const head = current ? windowHead(current.window) : null
    if (!current || !head?.hasMore || !head.nextCursor || current.window.stalled) {
      return
    }
    const generation = current.window.generation
    const requestedCursor = head.nextCursor
    const ticket = ++continuationEpoch.current
    setIsLoadingMore(true)
    setContinuationError(null)
    try {
      const page = await fetchCrossActionPlanExecutionFeedPins(viewMode, {
        category,
        cursor: requestedCursor,
        pageSize: 10,
      })
      if (ticket !== continuationEpoch.current) {
        return
      }
      const latest = queryClient.getQueryData<ExecutionPinsCacheState>(queryKey)
      if (!latest || latest.window.generation !== generation) {
        return
      }
      const appended = appendExecutionFeedWindow(latest.window, page, requestedCursor)
      queryClient.setQueryData<ExecutionPinsCacheState>(queryKey, { window: appended.window })
      if (appended.stalled) {
        setContinuationError(new Error('La suite des épingles n’a pas pu être chargée.'))
      }
    } catch (error) {
      if (ticket === continuationEpoch.current) {
        setContinuationError(error)
      }
    } finally {
      if (ticket === continuationEpoch.current) {
        setIsLoadingMore(false)
      }
    }
  }, [category, queryClient, queryKey, viewMode])
  const retryStalledContinuation = useCallback(async () => {
    if (
      continuationError instanceof ActionPlansApiError &&
      continuationError.code === 'cursor_context_mismatch'
    ) {
      await queryClient.refetchQueries({ queryKey })
      if (queryClient.getQueryState(queryKey)?.status === 'success') {
        setContinuationError(null)
      }
      return
    }
    queryClient.setQueryData<ExecutionPinsCacheState>(queryKey, (current) =>
      current ? { window: { ...current.window, stalled: false } } : current,
    )
    setContinuationError(null)
    await loadMore()
  }, [continuationError, loadMore, queryClient, queryKey])
  const head = query.data ? windowHead(query.data.window) : null
  return {
    ...query,
    hasNextPage: Boolean(head?.hasMore) && !query.data?.window.stalled,
    isFetchingNextPage: isLoadingMore,
    fetchNextPage: loadMore,
    continuationError,
    isRetryingStalledContinuation: isLoadingMore,
    retryStalledContinuation,
  }
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
  const submissionSlot = useRef<ClientSubmissionSlot | null>(null)
  return useMutation({
    mutationFn: async ({
      taskExecutionId,
      body,
    }: {
      taskExecutionId: string
      body: Omit<ActionPlanTaskCreateObservationRequest, 'client_submission_id'>
    }) => {
      const clientSubmissionId = clientSubmissionIdForFingerprint(
        submissionSlot,
        `${taskExecutionId}\n${body.text}`,
      )
      const response = await createObservationFromActionPlanTask(establishmentId, taskExecutionId, {
        ...body,
        client_submission_id: clientSubmissionId,
      })
      clearClientSubmissionId(submissionSlot)
      return response
    },
    onSuccess: () => {
      invalidateActionPlanExecutionSurfaces(queryClient, establishmentId, executionId)
    },
  })
}
