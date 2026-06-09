import { apiClient, withAuthRetry } from '@/api/client'

import { parseStandardApiError } from '@/lib/api-errors'

import type {
  ChatConversationDetail,
  ChatConversationListResponse,
  ChatCreateConversationResponse,
  ChatEligibleMembershipsResponse,
  ChatMessageListResponse,
  ChatStatus,
  ChatWsTicketResponse,
} from './types'

export const chatQueryKeys = {
  all: ['chat'] as const,
  status: (establishmentId: string) => ['chat', 'status', establishmentId] as const,
  conversations: (establishmentId: string) => ['chat', 'conversations', establishmentId] as const,
  conversation: (establishmentId: string, conversationId: string) =>
    ['chat', 'conversation', establishmentId, conversationId] as const,
  messages: (establishmentId: string, conversationId: string) =>
    ['chat', 'messages', establishmentId, conversationId] as const,
  eligibleMemberships: (establishmentId: string, query: string) =>
    ['chat', 'eligible-memberships', establishmentId, query] as const,
}

export class ChatApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'ChatApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code ?? null
  }
}

function getAuthHeaders(accessToken: string | null) {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : undefined
}

function parseError(response: Response, payload: unknown): ChatApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new ChatApiError({ status, detail, code })
}

function assertChatData<T>(result: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (result.response.ok && result.data !== undefined) {
    return result.data
  }

  throw parseError(result.response, result.error)
}

function chatPathParams(establishmentId: string) {
  return {
    path: {
      establishment_id: establishmentId,
    },
  }
}

function conversationPathParams(establishmentId: string, conversationId: string) {
  return {
    path: {
      establishment_id: establishmentId,
      conversation_id: conversationId,
    },
  }
}

export async function fetchChatStatus(establishmentId: string): Promise<ChatStatus> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/chat/status/', {
        params: chatPathParams(establishmentId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertChatData<ChatStatus>(result)
}

export async function fetchChatConversations(
  establishmentId: string,
): Promise<ChatConversationListResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/chat/conversations/', {
        params: chatPathParams(establishmentId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertChatData<ChatConversationListResponse>(result)
}

export async function fetchChatConversationDetail(
  establishmentId: string,
  conversationId: string,
): Promise<ChatConversationDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/chat/conversations/{conversation_id}/', {
        params: conversationPathParams(establishmentId, conversationId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertChatData<ChatConversationDetail>(result)
}

export async function fetchChatMessages(
  establishmentId: string,
  conversationId: string,
  options: { cursor?: string; pageSize?: number } = {},
): Promise<ChatMessageListResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET(
        '/api/v1/establishments/{establishment_id}/chat/conversations/{conversation_id}/messages/',
        {
          params: {
            ...conversationPathParams(establishmentId, conversationId),
            query: {
              ...(options.cursor ? { cursor: options.cursor } : {}),
              ...(options.pageSize ? { page_size: options.pageSize } : {}),
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChatData<ChatMessageListResponse>(result)
}

export async function fetchEligibleChatMemberships(
  establishmentId: string,
  query: string,
): Promise<ChatEligibleMembershipsResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/chat/eligible-memberships/', {
        params: {
          ...chatPathParams(establishmentId),
          query: query.trim() ? { q: query.trim() } : undefined,
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertChatData<ChatEligibleMembershipsResponse>(result)
}

export async function createDmConversation(
  establishmentId: string,
  membershipId: string,
): Promise<ChatCreateConversationResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/chat/conversations/dm/', {
        params: chatPathParams(establishmentId),
        headers: getAuthHeaders(accessToken),
        body: {
          membership_id: membershipId,
        },
      }),
    { refreshable: true },
  )

  return assertChatData<ChatCreateConversationResponse>(result)
}

export async function createGroupConversation(
  establishmentId: string,
  payload: { title: string; membershipIds: string[] },
): Promise<ChatCreateConversationResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/chat/conversations/groups/', {
        params: chatPathParams(establishmentId),
        headers: getAuthHeaders(accessToken),
        body: {
          title: payload.title,
          membership_ids: payload.membershipIds,
        },
      }),
    { refreshable: true },
  )

  return assertChatData<ChatCreateConversationResponse>(result)
}

export async function markConversationSeen(
  establishmentId: string,
  conversationId: string,
): Promise<void> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/chat/conversations/{conversation_id}/seen/',
        {
          params: conversationPathParams(establishmentId, conversationId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  if (!result.response.ok) {
    throw parseError(result.response, result.error)
  }
}

export async function issueChatWsTicket(establishmentId: string): Promise<ChatWsTicketResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/chat/ws-ticket/', {
        params: chatPathParams(establishmentId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertChatData<ChatWsTicketResponse>(result)
}
