import type { ChatConversationListItem, ChatMessage } from '../types'

export type ChatConversationSectionKey = 'dm' | 'group'

export type ChatConversationSectionGroup = {
  section: ChatConversationSectionKey
  label: string
  items: ChatConversationListItem[]
}

const SECTION_ORDER: ChatConversationSectionKey[] = ['dm', 'group']

const SECTION_LABELS: Record<ChatConversationSectionKey, string> = {
  dm: 'Messages directs',
  group: 'Groupes',
}

export function getConversationSectionKey(
  conversation: Pick<ChatConversationListItem, 'type'>,
): ChatConversationSectionKey {
  return conversation.type === 'dm' ? 'dm' : 'group'
}

export function groupConversationsByType(
  conversations: ChatConversationListItem[],
): ChatConversationSectionGroup[] {
  const buckets = new Map<ChatConversationSectionKey, ChatConversationListItem[]>()

  for (const conversation of conversations) {
    const section = getConversationSectionKey(conversation)
    const bucket = buckets.get(section)
    if (bucket) {
      bucket.push(conversation)
    } else {
      buckets.set(section, [conversation])
    }
  }

  return SECTION_ORDER.flatMap((section) => {
    const items = buckets.get(section)
    if (!items || items.length === 0) {
      return []
    }
    return [
      {
        section,
        label: SECTION_LABELS[section],
        items,
      },
    ]
  })
}

export function getConversationTitle(
  conversation: Pick<ChatConversationListItem, 'title' | 'type' | 'participants'>,
  viewerMembershipId: string | null,
): string {
  const explicitTitle = conversation.title.trim()
  if (explicitTitle) {
    return explicitTitle
  }

  if (conversation.type === 'dm') {
    const peer = conversation.participants.find(
      (participant) => participant.membership_id !== viewerMembershipId,
    )
    return peer?.display_name?.trim() || 'Message direct'
  }

  return 'Groupe'
}

export function formatChatRelativeTime(value: string | null | undefined): string {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }

  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()

  if (sameDay) {
    return new Intl.DateTimeFormat('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  const isYesterday =
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate()

  if (isYesterday) {
    return 'Hier'
  }

  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
  }).format(date)
}

export function formatChatMessageDayLabel(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(date)
}

export function isSameChatDay(first: string, second: string): boolean {
  const firstDate = new Date(first)
  const secondDate = new Date(second)
  if (Number.isNaN(firstDate.getTime()) || Number.isNaN(secondDate.getTime())) {
    return false
  }

  return (
    firstDate.getFullYear() === secondDate.getFullYear() &&
    firstDate.getMonth() === secondDate.getMonth() &&
    firstDate.getDate() === secondDate.getDate()
  )
}

export function buildMessageCursor(message: ChatMessage): string {
  return `${message.created_at}|${message.id}`
}

export function filterConversationsByQuery(
  conversations: ChatConversationListItem[],
  query: string,
  viewerMembershipId: string | null,
): ChatConversationListItem[] {
  const normalized = query.trim().toLowerCase()
  if (!normalized) {
    return conversations
  }

  return conversations.filter((conversation) => {
    const title = getConversationTitle(conversation, viewerMembershipId).toLowerCase()
    if (title.includes(normalized)) {
      return true
    }

    return conversation.participants.some((participant) =>
      participant.display_name.toLowerCase().includes(normalized),
    )
  })
}

export function hasUnreadConversations(conversations: ChatConversationListItem[]): boolean {
  return conversations.some((conversation) => conversation.unread)
}
