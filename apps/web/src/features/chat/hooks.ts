import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type InfiniteData,
} from '@tanstack/react-query'

import {
  chatQueryKeys,
  createDmConversation,
  createGroupConversation,
  fetchChatConversationDetail,
  fetchChatConversations,
  fetchChatMessages,
  fetchChatStatus,
  fetchEligibleChatMemberships,
  markConversationSeen,
} from './api'
import { buildMessageCursor } from './lib/chat-display'
import { patchConversationsOnMessageCreated } from './lib/chat-conversations-cache'
import type { ChatConversationListResponse, ChatMessage, ChatMessageListResponse } from './types'

export function useChatStatusQuery(establishmentId: string | null) {
  return useQuery({
    queryKey: establishmentId ? chatQueryKeys.status(establishmentId) : ['chat', 'status', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchChatStatus(establishmentId)
    },
    enabled: Boolean(establishmentId),
  })
}

export function useChatConversationsQuery(
  establishmentId: string | null,
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: establishmentId
      ? chatQueryKeys.conversations(establishmentId)
      : ['chat', 'conversations', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchChatConversations(establishmentId)
    },
    enabled: Boolean(establishmentId) && (options.enabled ?? true),
  })
}

export function useChatConversationDetailQuery(
  establishmentId: string | null,
  conversationId: string | null,
) {
  return useQuery({
    queryKey:
      establishmentId && conversationId
        ? chatQueryKeys.conversation(establishmentId, conversationId)
        : ['chat', 'conversation', 'none'],
    queryFn: () => {
      if (!establishmentId || !conversationId) {
        throw new Error('Conversation introuvable.')
      }
      return fetchChatConversationDetail(establishmentId, conversationId)
    },
    enabled: Boolean(establishmentId && conversationId),
  })
}

export function useChatMessagesInfiniteQuery(
  establishmentId: string | null,
  conversationId: string | null,
) {
  return useInfiniteQuery({
    queryKey:
      establishmentId && conversationId
        ? chatQueryKeys.messages(establishmentId, conversationId)
        : ['chat', 'messages', 'none'],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (!establishmentId || !conversationId) {
        throw new Error('Conversation introuvable.')
      }
      return fetchChatMessages(establishmentId, conversationId, {
        cursor: pageParam,
        pageSize: 50,
      })
    },
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more || lastPage.items.length === 0) {
        return undefined
      }
      return buildMessageCursor(lastPage.items[0]!)
    },
    enabled: Boolean(establishmentId && conversationId),
  })
}

export function useEligibleChatMembershipsQuery(
  establishmentId: string | null,
  query: string,
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: establishmentId
      ? chatQueryKeys.eligibleMemberships(establishmentId, query)
      : ['chat', 'eligible-memberships', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchEligibleChatMemberships(establishmentId, query)
    },
    enabled: Boolean(establishmentId) && (options.enabled ?? true),
  })
}

export function useCreateDmMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (membershipId: string) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return createDmConversation(establishmentId, membershipId)
    },
    onSuccess: () => {
      if (!establishmentId) {
        return
      }
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations(establishmentId) })
    },
  })
}

export function useCreateGroupMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: { title: string; membershipIds: string[] }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return createGroupConversation(establishmentId, payload)
    },
    onSuccess: () => {
      if (!establishmentId) {
        return
      }
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations(establishmentId) })
    },
  })
}

export function useMarkConversationSeenMutation(
  establishmentId: string | null,
  conversationId: string | null,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      if (!establishmentId || !conversationId) {
        throw new Error('Conversation introuvable.')
      }
      await markConversationSeen(establishmentId, conversationId)
    },
    onSuccess: () => {
      if (!establishmentId) {
        return
      }
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations(establishmentId) })
      if (conversationId) {
        void queryClient.invalidateQueries({
          queryKey: chatQueryKeys.conversation(establishmentId, conversationId),
        })
      }
    },
  })
}

type AppendChatMessageToCacheOptions = {
  viewerMembershipId: string | null
  activeConversationId: string | null
}

export function useAppendChatMessageToCache() {
  const queryClient = useQueryClient()

  return (
    establishmentId: string,
    conversationId: string,
    message: ChatMessage,
    options: AppendChatMessageToCacheOptions,
  ) => {
    queryClient.setQueryData<InfiniteData<ChatMessageListResponse>>(
      chatQueryKeys.messages(establishmentId, conversationId),
      (current) => {
        if (!current) {
          return current
        }

        const pages = [...current.pages]
        const lastPageIndex = pages.length - 1
        const lastPage = pages[lastPageIndex]
        if (!lastPage) {
          return current
        }

        if (lastPage.items.some((item) => item.id === message.id)) {
          return current
        }

        pages[lastPageIndex] = {
          ...lastPage,
          items: [...lastPage.items, message],
        }

        return {
          ...current,
          pages,
        }
      },
    )

    queryClient.setQueryData<ChatConversationListResponse>(
      chatQueryKeys.conversations(establishmentId),
      (current) =>
        patchConversationsOnMessageCreated(current, {
          conversationId,
          message,
          viewerMembershipId: options.viewerMembershipId,
          activeConversationId: options.activeConversationId,
        }),
    )

    void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations(establishmentId) })
  }
}
