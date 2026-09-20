import type { components } from '@/api/generated/types'

export type ChatStatus = components['schemas']['ChatStatus']
export type ChatConversationListItem = components['schemas']['ChatConversationListItem']
export type ChatConversationListResponse = components['schemas']['ChatConversationListResponse']
export type ChatConversationDetail = components['schemas']['ChatConversationDetail']
export type ChatParticipantSummary = components['schemas']['ChatParticipantSummary']
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

export type ChatAttachment = components['schemas']['ChatAttachment']
export type ChatMessageMention = components['schemas']['ChatMessageMention']
export type ChatReplyTo = components['schemas']['ChatReplyTo']
export type ChatReserveUploadResponse = components['schemas']['ChatReserveUploadResponse']
export type ChatSendMessageResponse = components['schemas']['ChatSendMessageResponse']
export type ChatUploadCompleteResponse = components['schemas']['ChatUploadCompleteResponse']

export type ChatSharedMediaResponse = components['schemas']['ChatSharedMediaResponse']

export type LocalChatMessageStatus = 'pending' | 'sent' | 'failed'
export type LocalChatAttachmentState =
  | 'reserving'
  | 'uploading'
  | 'finalizing'
  | 'ready'
  | 'failed'

export type LocalChatAttachment = {
  localAttachmentId: string
  uploadId: string | null
  filename: string
  contentType: string
  sizeBytes: number
  state: LocalChatAttachmentState
  previewUrl?: string
  progress?: number
}

export type LocalChatMessage = {
  clientMessageId: string
  conversationId: string
  body: string
  mentions: Array<Pick<ChatMessageMention, 'membership_id' | 'start' | 'end'>>
  replyToId: string | null
  replyPreview?: {
    authorDisplayName: string
    excerpt: string
    unavailable?: boolean
  } | null
  attachments: LocalChatAttachment[]
  status: LocalChatMessageStatus
  createdAt: string
  authorMembershipId: string
  authorDisplayName: string
  rejectCode?: string
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

export type ChatWsConversationUpdatedEvent = {
  type: 'conversation.updated'
  conversation_id: string
}

export type ChatWsServerEvent =
  | ChatWsMessageCreatedEvent
  | ChatWsMessageRejectedEvent
  | ChatWsGlobalAccessRevokedEvent
  | ChatWsConversationAccessRevokedEvent
  | ChatWsConversationUpdatedEvent
  | { type: 'auth.ok' }
  | { type: 'error'; code?: string; detail?: string }
