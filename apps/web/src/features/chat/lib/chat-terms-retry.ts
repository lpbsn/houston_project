import { isTermsAcceptanceRequired } from '@/lib/legal'

import type { LocalChatMessage } from '../types'

export function selectLocalMessagesToRetryAfterTermsAccept(
  messages: LocalChatMessage[],
): LocalChatMessage[] {
  return messages.filter(
    (message) =>
      message.status === 'failed' && isTermsAcceptanceRequired({ code: message.rejectCode }),
  )
}

export function asPendingLocalChatMessage(message: LocalChatMessage): LocalChatMessage {
  return {
    clientMessageId: message.clientMessageId,
    conversationId: message.conversationId,
    body: message.body,
    status: 'pending',
    createdAt: message.createdAt,
    authorMembershipId: message.authorMembershipId,
    authorDisplayName: message.authorDisplayName,
  }
}
