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

function membershipChatAvailable(
  membership: BootstrapResponse['active_membership'] | BootstrapResponse['memberships'][number],
  nextAvailable: boolean,
) {
  if (!membership || membership.chat_available === nextAvailable) {
    return membership
  }
  return { ...membership, chat_available: nextAvailable }
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
    const nextAvailable = status.can_access
    const nextActiveMembership = membershipChatAvailable(current.active_membership, nextAvailable)
    const nextMemberships = current.memberships.map((membership) =>
      membership.establishment_id === establishmentId
        ? membershipChatAvailable(membership, nextAvailable)
        : membership,
    )
    const sessionAligned = current.permission_hints.chat_available === nextAvailable
    const membershipsUnchanged = nextMemberships.every(
      (membership, index) => membership === current.memberships[index],
    )
    if (sessionAligned && nextActiveMembership === current.active_membership && membershipsUnchanged) {
      return current
    }
    return {
      ...current,
      active_membership: nextActiveMembership,
      memberships: nextMemberships,
      permission_hints: {
        ...current.permission_hints,
        chat_available: nextAvailable,
      },
    }
  })

  if (!isChatRuntimeAvailable(status)) {
    purgeEstablishmentChatOperationalQueries(queryClient, establishmentId)
  }
}
