import type { Query, QueryClient } from '@tanstack/react-query'

import { bootstrapQueryKey } from '@/features/auth/api'
import type { BootstrapResponse } from '@/features/auth/types'

import type { ChatStatus } from '../types'

import { isChatRuntimeAvailable } from './chat-availability'

export function isEstablishmentChatOperationalQuery(
  query: Query,
  establishmentId: string,
): boolean {
  const key = query.queryKey
  return key[0] === 'chat' && key[1] !== 'status' && key[2] === establishmentId
}

export function purgeEstablishmentChatOperationalQueries(
  queryClient: QueryClient,
  establishmentId: string,
) {
  queryClient.removeQueries({
    predicate: (query) => isEstablishmentChatOperationalQuery(query, establishmentId),
  })
}

export function applyChatAvailabilityFromStatus(
  queryClient: QueryClient,
  establishmentId: string,
  status: ChatStatus,
) {
  queryClient.setQueryData<BootstrapResponse>(bootstrapQueryKey, (current) => {
    if (!current) {
      return current
    }
    if (current.active_membership?.establishment_id !== establishmentId) {
      return current
    }
    if (current.permission_hints.chat_available === status.can_access) {
      return current
    }
    return {
      ...current,
      permission_hints: {
        ...current.permission_hints,
        chat_available: status.can_access,
      },
    }
  })

  if (!isChatRuntimeAvailable(status)) {
    purgeEstablishmentChatOperationalQueries(queryClient, establishmentId)
  }
}
