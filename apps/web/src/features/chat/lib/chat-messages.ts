import type { ChatMessage, LocalChatMessage } from '../types'

export function mergeServerAndLocalMessages(
  serverMessages: ChatMessage[],
  localMessages: LocalChatMessage[],
  conversationId: string,
): Array<
  | { kind: 'server'; message: ChatMessage }
  | { kind: 'local'; message: LocalChatMessage }
> {
  const pendingOrFailed = localMessages.filter(
    (message) =>
      message.conversationId === conversationId &&
      (message.status === 'pending' || message.status === 'failed'),
  )

  const serverClientIds = new Set(serverMessages.map((message) => message.client_message_id))
  const unmatchedLocal = pendingOrFailed.filter(
    (message) => !serverClientIds.has(message.clientMessageId),
  )

  const merged: Array<
    | { kind: 'server'; message: ChatMessage }
    | { kind: 'local'; message: LocalChatMessage }
  > = serverMessages.map((message) => ({ kind: 'server', message }))

  for (const message of unmatchedLocal) {
    merged.push({ kind: 'local', message })
  }

  merged.sort((left, right) => {
    const leftCreatedAt = left.kind === 'server' ? left.message.created_at : left.message.createdAt
    const rightCreatedAt =
      right.kind === 'server' ? right.message.created_at : right.message.createdAt
    if (leftCreatedAt === rightCreatedAt) {
      const leftId =
        left.kind === 'server' ? left.message.client_message_id : left.message.clientMessageId
      const rightId =
        right.kind === 'server' ? right.message.client_message_id : right.message.clientMessageId
      return leftId.localeCompare(rightId)
    }
    return leftCreatedAt.localeCompare(rightCreatedAt)
  })

  return merged
}

export function appendUniqueServerMessage(
  messages: ChatMessage[],
  incoming: ChatMessage,
): ChatMessage[] {
  if (messages.some((message) => message.id === incoming.id)) {
    return messages
  }
  if (messages.some((message) => message.client_message_id === incoming.client_message_id)) {
    return messages
  }

  return [...messages, incoming].sort((left, right) => {
    if (left.created_at === right.created_at) {
      return left.id.localeCompare(right.id)
    }
    return left.created_at.localeCompare(right.created_at)
  })
}
