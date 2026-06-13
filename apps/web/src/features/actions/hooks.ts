import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { invalidateActionMutationSurfaces } from '@/lib/query-invalidation'

import {
  acceptAction,
  actionsQueryKeys,
  cancelAction,
  createAction,
  fetchActionDetail,
  fetchExecutionFeed,
  markActionDone,
  reopenAction,
  reassignAction,
  searchEstablishmentUsers,
  establishmentUserSearchQueryKey,
  updateActionDueAt,
  validateAction,
} from './api'
import type { ActionCreateRequest, ExecutionViewMode } from './types'

function invalidateActionSurfaces(
  queryClient: ReturnType<typeof useQueryClient>,
  establishmentId: string,
) {
  invalidateActionMutationSurfaces(queryClient, establishmentId)
}

export function useExecutionFeedQuery(
  establishmentId: string | null,
  viewMode: ExecutionViewMode,
) {
  return useInfiniteQuery({
    queryKey: establishmentId
      ? actionsQueryKeys.feed(establishmentId, viewMode)
      : ['actions', 'execution-feed', 'none'],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchExecutionFeed(establishmentId, viewMode, {
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

export function useActionDetailQuery(establishmentId: string | null, actionId: string | null) {
  return useQuery({
    queryKey:
      establishmentId && actionId
        ? actionsQueryKeys.detail(establishmentId, actionId)
        : ['actions', 'detail', 'none'],
    queryFn: () => {
      if (!establishmentId || !actionId) {
        throw new Error('Action introuvable.')
      }
      return fetchActionDetail(establishmentId, actionId)
    },
    enabled: Boolean(establishmentId && actionId),
  })
}

export function useCreateActionMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: ActionCreateRequest) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return createAction(establishmentId, body)
    },
    onSuccess: () => {
      if (establishmentId) {
        invalidateActionSurfaces(queryClient, establishmentId)
      }
    },
  })
}

function useActionCommandMutation(
  establishmentId: string | null,
  actionId: string | null,
  command: (
    estId: string,
    actId: string,
  ) => Promise<import('./types').ActionDetail>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      if (!establishmentId || !actionId) {
        throw new Error('Action introuvable.')
      }
      return command(establishmentId, actionId)
    },
    onSuccess: () => {
      if (establishmentId) {
        invalidateActionSurfaces(queryClient, establishmentId)
      }
    },
  })
}

export function useAcceptActionMutation(establishmentId: string | null, actionId: string | null) {
  return useActionCommandMutation(establishmentId, actionId, acceptAction)
}

export function useMarkActionDoneMutation(establishmentId: string | null, actionId: string | null) {
  return useActionCommandMutation(establishmentId, actionId, markActionDone)
}

export function useValidateActionMutation(establishmentId: string | null, actionId: string | null) {
  return useActionCommandMutation(establishmentId, actionId, validateAction)
}

export function useReopenActionMutation(establishmentId: string | null, actionId: string | null) {
  return useActionCommandMutation(establishmentId, actionId, reopenAction)
}

export function useCancelActionMutation(establishmentId: string | null, actionId: string | null) {
  return useActionCommandMutation(establishmentId, actionId, cancelAction)
}

export function useReassignActionMutation(establishmentId: string | null, actionId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (assignedTo: string) => {
      if (!establishmentId || !actionId) {
        throw new Error('Action introuvable.')
      }
      return reassignAction(establishmentId, actionId, assignedTo)
    },
    onSuccess: () => {
      if (establishmentId) {
        invalidateActionSurfaces(queryClient, establishmentId)
      }
    },
  })
}

export function useUpdateActionDueAtMutation(
  establishmentId: string | null,
  actionId: string | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (dueAt: string) => {
      if (!establishmentId || !actionId) {
        throw new Error('Action introuvable.')
      }
      return updateActionDueAt(establishmentId, actionId, dueAt)
    },
    onSuccess: () => {
      if (establishmentId) {
        invalidateActionSurfaces(queryClient, establishmentId)
      }
    },
  })
}

export function useEstablishmentUserSearchQuery(
  establishmentId: string,
  query: string,
  options: { businessUnitId?: string } = {},
) {
  const trimmedQuery = query.trim()
  const businessUnitId = options.businessUnitId

  return useQuery({
    queryKey: establishmentUserSearchQueryKey(establishmentId, trimmedQuery, businessUnitId),
    queryFn: () =>
      searchEstablishmentUsers(establishmentId, trimmedQuery, {
        businessUnitId,
      }),
    enabled: Boolean(establishmentId) && trimmedQuery.length >= 2,
  })
}
