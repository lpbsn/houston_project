import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  commentsQueryKeys,
  createExecutionComment,
  createSignalComment,
  fetchExecutionComments,
  fetchSignalComments,
  mentionUserSearchQueryKey,
  resolveExecutionComment,
  searchEstablishmentUsersForMentions,
  unresolveExecutionComment,
} from './api'
import type { CommentCreateRequest } from './types'

const MENTION_SEARCH_MIN_LENGTH = 2

export function useSignalCommentsQuery(establishmentId: string | null, signalId: string | null) {
  return useQuery({
    queryKey:
      establishmentId && signalId
        ? commentsQueryKeys.signalList(establishmentId, signalId)
        : ['comments', 'signal', 'none'],
    queryFn: () => {
      if (!establishmentId || !signalId) {
        throw new Error('Observation introuvable.')
      }
      return fetchSignalComments(establishmentId, signalId)
    },
    enabled: Boolean(establishmentId && signalId),
  })
}

export function useExecutionCommentsQuery(
  establishmentId: string | null,
  executionId: string | null,
) {
  return useQuery({
    queryKey:
      establishmentId && executionId
        ? commentsQueryKeys.executionList(establishmentId, executionId)
        : ['comments', 'action-plan-execution', 'none'],
    queryFn: () => {
      if (!establishmentId || !executionId) {
        throw new Error('Exécution introuvable.')
      }
      return fetchExecutionComments(establishmentId, executionId)
    },
    enabled: Boolean(establishmentId && executionId),
  })
}

export function useMentionUserSearchQuery(establishmentId: string | null, query: string) {
  const normalizedQuery = query.trim()

  return useQuery({
    queryKey:
      establishmentId && normalizedQuery.length >= MENTION_SEARCH_MIN_LENGTH
        ? mentionUserSearchQueryKey(establishmentId, normalizedQuery)
        : ['comments', 'mention-search', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return searchEstablishmentUsersForMentions(establishmentId, normalizedQuery)
    },
    enabled: Boolean(establishmentId && normalizedQuery.length >= MENTION_SEARCH_MIN_LENGTH),
  })
}

export function useCreateSignalCommentMutation(
  establishmentId: string | null,
  signalId: string | null,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CommentCreateRequest) => {
      if (!establishmentId || !signalId) {
        throw new Error('Observation introuvable.')
      }
      return createSignalComment(establishmentId, signalId, payload)
    },
    onSuccess: () => {
      if (establishmentId && signalId) {
        void queryClient.invalidateQueries({
          queryKey: commentsQueryKeys.signalList(establishmentId, signalId),
        })
      }
    },
  })
}

export function useCreateExecutionCommentMutation(
  establishmentId: string | null,
  executionId: string | null,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CommentCreateRequest) => {
      if (!establishmentId || !executionId) {
        throw new Error('Exécution introuvable.')
      }
      return createExecutionComment(establishmentId, executionId, payload)
    },
    onSuccess: () => {
      if (establishmentId && executionId) {
        void queryClient.invalidateQueries({
          queryKey: commentsQueryKeys.executionList(establishmentId, executionId),
        })
      }
    },
  })
}

export function useResolveExecutionCommentMutation(
  establishmentId: string | null,
  executionId: string | null,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (commentId: string) => {
      if (!establishmentId || !executionId) {
        throw new Error('Exécution introuvable.')
      }
      return resolveExecutionComment(establishmentId, executionId, commentId)
    },
    onSuccess: () => {
      if (establishmentId && executionId) {
        void queryClient.invalidateQueries({
          queryKey: commentsQueryKeys.executionList(establishmentId, executionId),
        })
      }
    },
  })
}

export function useUnresolveExecutionCommentMutation(
  establishmentId: string | null,
  executionId: string | null,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (commentId: string) => {
      if (!establishmentId || !executionId) {
        throw new Error('Exécution introuvable.')
      }
      return unresolveExecutionComment(establishmentId, executionId, commentId)
    },
    onSuccess: () => {
      if (establishmentId && executionId) {
        void queryClient.invalidateQueries({
          queryKey: commentsQueryKeys.executionList(establishmentId, executionId),
        })
      }
    },
  })
}
