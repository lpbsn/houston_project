import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type InfiniteData,
  type QueryClient,
} from '@tanstack/react-query'
import { useEffect } from 'react'

import {
  addGroupParticipant,
  chatQueryKeys,
  createDmConversation,
  createGroupConversation,
  deleteGroupConversation,
  fetchChatConversationDetail,
  fetchChatConversations,
  fetchChatMessages,
  fetchChatStatus,
  fetchEligibleChatMemberships,
  hideDmConversation,
  leaveGroupConversation,
  markConversationSeen,
  pinConversation,
  promoteGroupParticipant,
  removeGroupParticipant,
  unpinConversation,
} from './api'
import { applyChatAvailabilityFromStatus } from './lib/apply-chat-availability-cache'
import {
  isChatRuntimeAvailable,
  resolveChatNavVisible,
} from './lib/chat-availability'
import { buildMessageCursor } from './lib/chat-display'
import { appendUniqueServerMessage } from './lib/chat-messages'
import {
  compareConversationsForList,
  patchConversationsOnMessageCreated,
} from './lib/chat-conversations-cache'
import { purgeConversationClientState } from './lib/purge-conversation-client-state'
import type { ChatConversationListResponse, ChatMessage, ChatMessageListResponse } from './types'

type ChatStatusQueryOptions = {
  enabled?: boolean
  refetchOnWindowFocus?: boolean
  staleTime?: number
}

export function useChatStatusQuery(
  establishmentId: string | null,
  options: ChatStatusQueryOptions = {},
) {
  return useQuery({
    queryKey: establishmentId ? chatQueryKeys.status(establishmentId) : ['chat', 'status', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchChatStatus(establishmentId)
    },
    enabled: Boolean(establishmentId) && (options.enabled ?? true),
    refetchOnWindowFocus: options.refetchOnWindowFocus,
    staleTime: options.staleTime,
  })
}

type UseChatAvailabilityOptions = {
  establishmentId: string | null
  hasOperationalAccess: boolean
  bootstrapChatAvailable: boolean
}

export function useChatAvailability({
  establishmentId,
  hasOperationalAccess,
  bootstrapChatAvailable,
}: UseChatAvailabilityOptions) {
  const queryClient = useQueryClient()
  const statusQuery = useChatStatusQuery(establishmentId, {
    enabled: Boolean(establishmentId) && hasOperationalAccess,
  })

  const statusResolved = statusQuery.isSuccess
  const status = statusQuery.data
  const isRuntimeAvailable = isChatRuntimeAvailable(status)
  const isNavVisible = resolveChatNavVisible({
    hasOperationalAccess,
    status,
    statusResolved,
    bootstrapChatAvailable,
  })

  useEffect(() => {
    if (!establishmentId || !status) {
      return
    }
    applyChatAvailabilityFromStatus(queryClient, establishmentId, status)
  }, [establishmentId, queryClient, status])

  return {
    status,
    isLoading: statusQuery.isLoading,
    isError: statusQuery.isError,
    isNavVisible,
    isRuntimeAvailable,
    statusResolved,
  }
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
  options: { enabled?: boolean; conversationId?: string | null } = {},
) {
  const conversationId = options.conversationId ?? null
  return useQuery({
    queryKey: establishmentId
      ? chatQueryKeys.eligibleMemberships(establishmentId, query, conversationId)
      : ['chat', 'eligible-memberships', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchEligibleChatMemberships(establishmentId, query, { conversationId })
    },
    enabled: Boolean(establishmentId) && (options.enabled ?? true),
  })
}

export function invalidateConversationStructureQueries(
  queryClient: QueryClient,
  establishmentId: string,
  conversationId: string,
) {
  void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations(establishmentId) })
  void queryClient.invalidateQueries({
    queryKey: chatQueryKeys.conversation(establishmentId, conversationId),
  })
  void queryClient.invalidateQueries({
    queryKey: chatQueryKeys.eligibleMembershipsForConversation(establishmentId, conversationId),
  })
}

export function useAddGroupParticipantMutation(
  establishmentId: string | null,
  conversationId: string | null,
) {
  return useMutation({
    mutationFn: async (membershipId: string) => {
      if (!establishmentId || !conversationId) {
        throw new Error('Conversation introuvable.')
      }
      await addGroupParticipant(establishmentId, conversationId, membershipId)
    },
  })
}

export function useRemoveGroupParticipantMutation(
  establishmentId: string | null,
  conversationId: string | null,
) {
  return useMutation({
    mutationFn: async (membershipId: string) => {
      if (!establishmentId || !conversationId) {
        throw new Error('Conversation introuvable.')
      }
      await removeGroupParticipant(establishmentId, conversationId, membershipId)
    },
  })
}

export function usePromoteGroupParticipantMutation(
  establishmentId: string | null,
  conversationId: string | null,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (membershipId: string) => {
      if (!establishmentId || !conversationId) {
        throw new Error('Conversation introuvable.')
      }
      await promoteGroupParticipant(establishmentId, conversationId, membershipId)
    },
    onSuccess: () => {
      if (!establishmentId || !conversationId) {
        return
      }
      invalidateConversationStructureQueries(queryClient, establishmentId, conversationId)
    },
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

type ConversationActionOptions = {
  clearLocalMessages?: (conversationId: string) => void
  onRemoved?: (conversationId: string) => void
}

function useConversationRemovalMutation(
  establishmentId: string | null,
  mutationFn: (conversationId: string) => Promise<void>,
  options: ConversationActionOptions = {},
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (conversationId: string) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      await mutationFn(conversationId)
      return conversationId
    },
    onSuccess: (conversationId) => {
      if (!establishmentId) {
        return
      }
      purgeConversationClientState(queryClient, {
        establishmentId,
        conversationId,
        clearLocalMessages: options.clearLocalMessages,
      })
      options.onRemoved?.(conversationId)
    },
  })
}

export function usePinConversationMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (conversationId: string) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      await pinConversation(establishmentId, conversationId)
      return conversationId
    },
    onSuccess: (conversationId) => {
      if (!establishmentId) {
        return
      }
      queryClient.setQueryData<ChatConversationListResponse>(
        chatQueryKeys.conversations(establishmentId),
        (current) => {
          if (!current) {
            return current
          }
          const items = current.items.map((item) =>
            item.id === conversationId ? { ...item, pinned: true } : item,
          )
          return { items: [...items].sort(compareConversationsForList) }
        },
      )
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations(establishmentId) })
      void queryClient.invalidateQueries({
        queryKey: chatQueryKeys.conversation(establishmentId, conversationId),
      })
    },
  })
}

export function useUnpinConversationMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (conversationId: string) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      await unpinConversation(establishmentId, conversationId)
      return conversationId
    },
    onSuccess: (conversationId) => {
      if (!establishmentId) {
        return
      }
      queryClient.setQueryData<ChatConversationListResponse>(
        chatQueryKeys.conversations(establishmentId),
        (current) => {
          if (!current) {
            return current
          }
          const items = current.items.map((item) =>
            item.id === conversationId ? { ...item, pinned: false } : item,
          )
          return { items: [...items].sort(compareConversationsForList) }
        },
      )
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations(establishmentId) })
      void queryClient.invalidateQueries({
        queryKey: chatQueryKeys.conversation(establishmentId, conversationId),
      })
    },
  })
}

export function useHideDmMutation(
  establishmentId: string | null,
  options: ConversationActionOptions = {},
) {
  return useConversationRemovalMutation(
    establishmentId,
    async (conversationId) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      await hideDmConversation(establishmentId, conversationId)
    },
    options,
  )
}

export function useLeaveGroupMutation(
  establishmentId: string | null,
  options: ConversationActionOptions = {},
) {
  return useConversationRemovalMutation(
    establishmentId,
    async (conversationId) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      await leaveGroupConversation(establishmentId, conversationId)
    },
    options,
  )
}

export function useDeleteGroupMutation(
  establishmentId: string | null,
  options: ConversationActionOptions = {},
) {
  return useConversationRemovalMutation(
    establishmentId,
    async (conversationId) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      await deleteGroupConversation(establishmentId, conversationId)
    },
    options,
  )
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
        const recentPage = pages[0]
        if (!recentPage) {
          return current
        }

        pages[0] = {
          ...recentPage,
          items: appendUniqueServerMessage(recentPage.items, message),
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
