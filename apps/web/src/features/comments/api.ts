import { apiClient, withAuthRetry } from '@/api/client'

import { parseStandardApiError } from '@/lib/api-errors'

import type {
  ActionCommentListItem,
  ActionCommentThreadItem,
  CommentCreateRequest,
  CommentItem,
  ExecutionCommentListItem,
  ExecutionCommentThreadItem,
  MentionUserSearchResult,
} from './types'

export const commentsQueryKeys = {
  all: ['comments'] as const,
  signalList: (establishmentId: string, signalId: string) =>
    ['comments', 'signal', establishmentId, signalId] as const,
  actionList: (establishmentId: string, actionId: string) =>
    ['comments', 'action', establishmentId, actionId] as const,
  executionList: (establishmentId: string, executionId: string) =>
    ['comments', 'action-plan-execution', establishmentId, executionId] as const,
}

export const mentionUserSearchQueryKey = (establishmentId: string, query: string) =>
  ['comments', 'mention-search', establishmentId, query] as const

export class CommentsApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'CommentsApiError'
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

function parseError(response: Response, payload: unknown): CommentsApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new CommentsApiError({ status, detail, code })
}

function assertCommentsData<T>(result: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (result.response.ok && result.data !== undefined) {
    return result.data
  }

  throw parseError(result.response, result.error)
}

export async function fetchSignalComments(
  establishmentId: string,
  signalId: string,
): Promise<CommentItem[]> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/signals/{signal_id}/comments/', {
        params: {
          path: {
            establishment_id: establishmentId,
            signal_id: signalId,
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertCommentsData<CommentItem[]>(result)
}

export async function fetchActionComments(
  establishmentId: string,
  actionId: string,
): Promise<ActionCommentListItem[]> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/actions/{action_id}/comments/', {
        params: {
          path: {
            establishment_id: establishmentId,
            action_id: actionId,
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertCommentsData<ActionCommentListItem[]>(result)
}

export async function createSignalComment(
  establishmentId: string,
  signalId: string,
  payload: CommentCreateRequest,
): Promise<CommentItem> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/signals/{signal_id}/comments/', {
        params: {
          path: {
            establishment_id: establishmentId,
            signal_id: signalId,
          },
        },
        body: payload,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertCommentsData<CommentItem>(result)
}

export async function createActionComment(
  establishmentId: string,
  actionId: string,
  payload: CommentCreateRequest,
): Promise<CommentItem> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/actions/{action_id}/comments/', {
        params: {
          path: {
            establishment_id: establishmentId,
            action_id: actionId,
          },
        },
        body: payload,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertCommentsData<CommentItem>(result)
}

export async function resolveActionComment(
  establishmentId: string,
  actionId: string,
  commentId: string,
): Promise<ActionCommentThreadItem> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/actions/{action_id}/comments/{comment_id}/resolve/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              action_id: actionId,
              comment_id: commentId,
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertCommentsData<ActionCommentThreadItem>(result)
}

export async function unresolveActionComment(
  establishmentId: string,
  actionId: string,
  commentId: string,
): Promise<ActionCommentThreadItem> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/actions/{action_id}/comments/{comment_id}/unresolve/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              action_id: actionId,
              comment_id: commentId,
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertCommentsData<ActionCommentThreadItem>(result)
}

export async function fetchExecutionComments(
  establishmentId: string,
  executionId: string,
): Promise<ExecutionCommentListItem[]> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/comments/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              execution_id: executionId,
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertCommentsData<ExecutionCommentListItem[]>(result)
}

export async function createExecutionComment(
  establishmentId: string,
  executionId: string,
  payload: CommentCreateRequest,
): Promise<CommentItem> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/comments/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              execution_id: executionId,
            },
          },
          body: payload,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertCommentsData<CommentItem>(result)
}

export async function resolveExecutionComment(
  establishmentId: string,
  executionId: string,
  commentId: string,
): Promise<ExecutionCommentThreadItem> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/comments/{comment_id}/resolve/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              execution_id: executionId,
              comment_id: commentId,
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertCommentsData<ExecutionCommentThreadItem>(result)
}

export async function unresolveExecutionComment(
  establishmentId: string,
  executionId: string,
  commentId: string,
): Promise<ExecutionCommentThreadItem> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/comments/{comment_id}/unresolve/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              execution_id: executionId,
              comment_id: commentId,
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertCommentsData<ExecutionCommentThreadItem>(result)
}

export async function searchEstablishmentUsersForMentions(
  establishmentId: string,
  query: string,
): Promise<MentionUserSearchResult[]> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/users/search/', {
        params: {
          path: { establishment_id: establishmentId },
          query: { q: query },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertCommentsData<MentionUserSearchResult[]>(result)
}
