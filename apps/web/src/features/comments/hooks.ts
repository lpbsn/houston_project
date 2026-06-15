import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  commentsQueryKeys,
  createActionComment,
  createSignalComment,
  fetchActionComments,
  fetchSignalComments,
  mentionUserSearchQueryKey,
  searchEstablishmentUsersForMentions,
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
        throw new Error('Signal introuvable.')
      }
      return fetchSignalComments(establishmentId, signalId)
    },
    enabled: Boolean(establishmentId && signalId),
  })
}

export function useActionCommentsQuery(establishmentId: string | null, actionId: string | null) {
  return useQuery({
    queryKey:
      establishmentId && actionId
        ? commentsQueryKeys.actionList(establishmentId, actionId)
        : ['comments', 'action', 'none'],
    queryFn: () => {
      if (!establishmentId || !actionId) {
        throw new Error('Action introuvable.')
      }
      return fetchActionComments(establishmentId, actionId)
    },
    enabled: Boolean(establishmentId && actionId),
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
        throw new Error('Signal introuvable.')
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

export function useCreateActionCommentMutation(
  establishmentId: string | null,
  actionId: string | null,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CommentCreateRequest) => {
      if (!establishmentId || !actionId) {
        throw new Error('Action introuvable.')
      }
      return createActionComment(establishmentId, actionId, payload)
    },
    onSuccess: () => {
      if (establishmentId && actionId) {
        void queryClient.invalidateQueries({
          queryKey: commentsQueryKeys.actionList(establishmentId, actionId),
        })
      }
    },
  })
}
