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
  const next: LocalChatMessage = { ...message, status: 'pending' }
  delete next.rejectCode
  return next
}
