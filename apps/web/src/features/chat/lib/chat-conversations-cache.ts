import type { ChatConversationListItem, ChatConversationListResponse, ChatMessage } from '../types'

import { compareChatMessagesAscending } from './chat-messages'

export function shouldMarkConversationUnread(options: {
  authorMembershipId: string
  viewerMembershipId: string | null
  conversationId: string
  activeConversationId: string | null
}): boolean {
  const { authorMembershipId, viewerMembershipId, conversationId, activeConversationId } = options

  if (!viewerMembershipId) {
    return false
  }
  if (authorMembershipId === viewerMembershipId) {
    return false
  }
  if (conversationId === activeConversationId) {
    return false
  }

  return true
}

export function buildLastMessagePreview(message: ChatMessage) {
  return {
    id: message.id,
    author_membership_id: message.author_membership_id,
    author_display_name: message.author_display_name,
    body: message.body,
    created_at: message.created_at,
  }
}

export function compareConversationsForList(
  left: ChatConversationListItem,
  right: ChatConversationListItem,
): number {
  if (left.pinned !== right.pinned) {
    return left.pinned ? -1 : 1
  }
  const leftTime = left.last_message_at ?? left.created_at
  const rightTime = right.last_message_at ?? right.created_at
  if (leftTime !== rightTime) {
    return rightTime.localeCompare(leftTime)
  }
  if (left.created_at !== right.created_at) {
    return right.created_at.localeCompare(left.created_at)
  }
  return right.id.localeCompare(left.id)
}

export function patchConversationsOnMessageCreated(
  current: ChatConversationListResponse | undefined,
  options: {
    conversationId: string
    message: ChatMessage
    viewerMembershipId: string | null
    activeConversationId: string | null
  },
): ChatConversationListResponse | undefined {
  if (!current) {
    return current
  }

  const { conversationId, message, viewerMembershipId, activeConversationId } = options
  const shouldIncrementUnread = shouldMarkConversationUnread({
    authorMembershipId: message.author_membership_id,
    viewerMembershipId,
    conversationId,
    activeConversationId,
  })
  const preview = buildLastMessagePreview(message)

  const items = current.items.map((item) => {
    if (item.id !== conversationId) {
      return item
    }
    if (item.last_message_preview?.id === message.id) {
      return item
    }
    if (
      item.last_message_preview &&
      compareChatMessagesAscending(item.last_message_preview, message) >= 0
    ) {
      return item
    }

    const unreadCount = shouldIncrementUnread ? item.unread_count + 1 : item.unread_count

    return {
      ...item,
      unread: unreadCount > 0,
      unread_count: unreadCount,
      last_message_at: message.created_at,
      last_message_preview: preview,
    }
  })

  const sorted = [...items].sort(compareConversationsForList)

  return { items: sorted }
}
