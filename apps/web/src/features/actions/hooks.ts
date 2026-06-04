import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { signalsQueryKeys } from '@/features/signals/api'

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
  updateActionDueAt,
  validateAction,
} from './api'
import type { ActionCreateRequest, ExecutionViewMode } from './types'

function invalidateActionSurfaces(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: actionsQueryKeys.all })
  void queryClient.invalidateQueries({ queryKey: signalsQueryKeys.all })
}

export function useExecutionFeedQuery(
  establishmentId: string | null,
  viewMode: ExecutionViewMode,
) {
  return useQuery({
    queryKey: establishmentId
      ? actionsQueryKeys.feed(establishmentId, viewMode)
      : ['actions', 'execution-feed', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchExecutionFeed(establishmentId, viewMode)
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
      invalidateActionSurfaces(queryClient)
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
      invalidateActionSurfaces(queryClient)
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
      invalidateActionSurfaces(queryClient)
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
      invalidateActionSurfaces(queryClient)
    },
  })
}
