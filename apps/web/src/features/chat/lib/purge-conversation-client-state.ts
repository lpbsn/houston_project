import type { QueryClient } from '@tanstack/react-query'

import { chatQueryKeys } from '../api'
import type { ChatConversationListResponse } from '../types'

export type PurgeConversationClientStateOptions = {
  establishmentId: string
  conversationId: string
  clearLocalMessages?: (conversationId: string) => void
}

export function purgeConversationClientState(
  queryClient: QueryClient,
  options: PurgeConversationClientStateOptions,
): void {
  const { establishmentId, conversationId, clearLocalMessages } = options

  queryClient.setQueryData<ChatConversationListResponse>(
    chatQueryKeys.conversations(establishmentId),
    (current) => {
      if (!current) {
        return current
      }
      return {
        items: current.items.filter((item) => item.id !== conversationId),
      }
    },
  )

  queryClient.removeQueries({
    queryKey: chatQueryKeys.conversation(establishmentId, conversationId),
  })
  queryClient.removeQueries({
    queryKey: chatQueryKeys.messages(establishmentId, conversationId),
  })

  clearLocalMessages?.(conversationId)
}
