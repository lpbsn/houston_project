import type { components } from '@/api/generated/types'

export type ChatStatus = components['schemas']['ChatStatus']
export type ChatConversationListItem = components['schemas']['ChatConversationListItem']
export type ChatConversationListResponse = components['schemas']['ChatConversationListResponse']
export type ChatConversationDetail = components['schemas']['ChatConversationDetail']
export type ChatMessage = components['schemas']['ChatMessage']
export type ChatMessageListResponse = components['schemas']['ChatMessageListResponse']
export type ChatEligibleMembership = components['schemas']['ChatMembershipSummary']
export type ChatEligibleMembershipsResponse = components['schemas']['ChatEligibleMembershipsResponse']
export type ChatCreateConversationResponse = components['schemas']['ChatCreateConversationResponse']
export type ChatWsTicketResponse = components['schemas']['ChatWsTicketResponse']

export type ChatConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'disconnected'

export type LocalChatMessageStatus = 'pending' | 'sent' | 'failed'

export type LocalChatMessage = {
  clientMessageId: string
  conversationId: string
  body: string
  status: LocalChatMessageStatus
  createdAt: string
  authorMembershipId: string
  authorDisplayName: string
}

export type ChatWsMessageCreatedEvent = {
  type: 'message.created'
  conversation_id: string
  message: ChatMessage
}

export type ChatWsMessageRejectedEvent = {
  type: 'message.rejected'
  client_message_id?: string
  code: string
  detail: string
}

export type ChatWsGlobalAccessRevokedEvent = {
  type: 'access.revoked'
  reason: string
}

export type ChatWsConversationAccessRevokedEvent = {
  type: 'conversation.access_revoked'
  conversation_id: string
  reason: string
}

/** @deprecated Use ChatWsConversationAccessRevokedEvent */
export type ChatWsAccessRevokedEvent = ChatWsConversationAccessRevokedEvent

export type ChatWsServerEvent =
  | ChatWsMessageCreatedEvent
  | ChatWsMessageRejectedEvent
  | ChatWsGlobalAccessRevokedEvent
  | ChatWsConversationAccessRevokedEvent
  | { type: 'auth.ok' }
  | { type: 'error'; code?: string; detail?: string }
