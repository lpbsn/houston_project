import type { ChatConversationListResponse, ChatMessage } from '../types'

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
  const unread = shouldMarkConversationUnread({
    authorMembershipId: message.author_membership_id,
    viewerMembershipId,
    conversationId,
    activeConversationId,
  })
  const preview = buildLastMessagePreview(message)

  const items = current.items.map((item) =>
    item.id === conversationId
      ? {
          ...item,
          unread,
          last_message_at: message.created_at,
          last_message_preview: preview,
        }
      : item,
  )

  const sorted = [...items].sort((left, right) => {
    const leftTime = left.last_message_at ?? ''
    const rightTime = right.last_message_at ?? ''
    if (leftTime === rightTime) {
      return right.id.localeCompare(left.id)
    }
    return rightTime.localeCompare(leftTime)
  })

  return { items: sorted }
}
