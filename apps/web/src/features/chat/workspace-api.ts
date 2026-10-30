import { apiClient, withAuthRetry } from '@/api/client'
import type { components } from '@/api/generated/types'
import { ChatApiError } from './api'
import { parseStandardApiError } from '@/lib/api-errors'
export type WorkspaceResponse = components['schemas']['WorkspaceResponse']
export type WorkspaceItem = components['schemas']['WorkspaceItem']
export type NotificationMode = 'all' | 'mentions' | 'silent'
export type WorkspaceFilter = {
  tab: 'plans' | 'mentions' | 'search'
  q?: string
  cursor?: string
  unresolved?: boolean
  author_id?: string
  after?: string
  before?: string
  files_only?: boolean
  execution_id?: string
}
const headers = (token: string | null) => (token ? { Authorization: `Bearer ${token}` } : undefined)
function result<T>(r: { response: Response; data?: T; error?: unknown }): T {
  if (r.response.ok && r.data !== undefined) return r.data
  throw new ChatApiError(parseStandardApiError(r.response, r.error))
}
export async function fetchWorkspace(establishmentId: string, filter: WorkspaceFilter) {
  return result(
    await withAuthRetry((token) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/chat/workspace/', {
        params: { path: { establishment_id: establishmentId }, query: filter },
        headers: headers(token),
      }),
    ),
  )
}
export async function messageTool(
  establishmentId: string,
  messageId: string,
  body: components['schemas']['MessageToolRequest'],
) {
  return result(
    await withAuthRetry((token) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/chat/messages/{message_id}/tools/',
        {
          params: { path: { establishment_id: establishmentId, message_id: messageId } },
          body,
          headers: headers(token),
        },
      ),
    ),
  )
}
export async function fetchSourceMessage(establishmentId: string, messageId: string) {
  return result(
    await withAuthRetry((token) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/chat/messages/{message_id}/tools/', {
        params: { path: { establishment_id: establishmentId, message_id: messageId } },
        headers: headers(token),
      }),
    ),
  )
}
export async function commentTool(
  establishmentId: string,
  commentId: string,
  body: components['schemas']['CommentToolRequest'],
) {
  return result(
    await withAuthRetry((token) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/chat/plan-comments/{comment_id}/tools/',
        {
          params: { path: { establishment_id: establishmentId, comment_id: commentId } },
          body,
          headers: headers(token),
        },
      ),
    ),
  )
}
export async function setConversationNotifications(
  establishmentId: string,
  conversationId: string,
  mode: NotificationMode,
) {
  return result(
    await withAuthRetry((token) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/chat/conversations/{conversation_id}/notifications/',
        {
          params: { path: { establishment_id: establishmentId, conversation_id: conversationId } },
          body: { mode, seen: false },
          headers: headers(token),
        },
      ),
    ),
  )
}
export async function setPlanDiscussionPreference(
  establishmentId: string,
  executionId: string,
  body: { mode?: NotificationMode; seen?: boolean; seen_through?: string },
) {
  return result(
    await withAuthRetry((token) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/chat/plan-discussions/{execution_id}/preferences/',
        {
          params: { path: { establishment_id: establishmentId, execution_id: executionId } },
          body: { seen: false, ...body },
          headers: headers(token),
        },
      ),
    ),
  )
}
export async function fetchPlanDiscussionPreference(establishmentId: string, executionId: string) {
  return result(
    await withAuthRetry((token) =>
      apiClient.GET(
        '/api/v1/establishments/{establishment_id}/chat/plan-discussions/{execution_id}/preferences/',
        {
          params: { path: { establishment_id: establishmentId, execution_id: executionId } },
          headers: headers(token),
        },
      ),
    ),
  )
}
