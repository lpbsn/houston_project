import { apiClient, withAuthRetry } from '@/api/client'

import { parseStandardApiError } from '@/lib/api-errors'

import type {
  ActionCreateRequest,
  ActionDetail,
  ExecutionFeedResponse,
  ExecutionViewMode,
  ScopedUserSearchResult,
} from './types'

export const actionsQueryKeys = {
  all: ['actions'] as const,
  feed: (establishmentId: string, viewMode: ExecutionViewMode) =>
    ['actions', 'execution-feed', establishmentId, viewMode] as const,
  detail: (establishmentId: string, actionId: string) =>
    ['actions', 'detail', establishmentId, actionId] as const,
}

export const establishmentUserSearchQueryKey = (
  establishmentId: string,
  query: string,
  businessUnitId?: string,
) => ['users', 'search', establishmentId, query, businessUnitId ?? null] as const

export type EstablishmentUserSearchOptions = {
  businessUnitId?: string
}

export class ActionsApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'ActionsApiError'
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

function parseError(response: Response, payload: unknown): ActionsApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new ActionsApiError({ status, detail, code })
}

function assertActionData<T>(result: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (result.response.ok && result.data) {
    return result.data
  }

  throw parseError(result.response, result.error)
}

function actionPathParams(establishmentId: string, actionId: string) {
  return {
    path: {
      establishment_id: establishmentId,
      action_id: actionId,
    },
  }
}

export async function fetchExecutionFeed(
  establishmentId: string,
  viewMode: ExecutionViewMode,
): Promise<ExecutionFeedResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/execution-feed/', {
        params: {
          path: { establishment_id: establishmentId },
          query: { view_mode: viewMode },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertActionData<ExecutionFeedResponse>(result)
}

export async function fetchActionDetail(
  establishmentId: string,
  actionId: string,
): Promise<ActionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/actions/{action_id}/', {
        params: actionPathParams(establishmentId, actionId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertActionData<ActionDetail>(result)
}

export async function createAction(
  establishmentId: string,
  body: ActionCreateRequest,
): Promise<ActionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/actions/', {
        params: {
          path: { establishment_id: establishmentId },
        },
        body,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertActionData<ActionDetail>(result)
}

async function postActionCommand(
  establishmentId: string,
  actionId: string,
  command:
    | 'accept'
    | 'cancel'
    | 'mark-done'
    | 'reopen'
    | 'validate',
): Promise<ActionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        `/api/v1/establishments/{establishment_id}/actions/{action_id}/${command}/` as '/api/v1/establishments/{establishment_id}/actions/{action_id}/accept/',
        {
          params: actionPathParams(establishmentId, actionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertActionData<ActionDetail>(result)
}

export const acceptAction = (establishmentId: string, actionId: string) =>
  postActionCommand(establishmentId, actionId, 'accept')

export const markActionDone = (establishmentId: string, actionId: string) =>
  postActionCommand(establishmentId, actionId, 'mark-done')

export const validateAction = (establishmentId: string, actionId: string) =>
  postActionCommand(establishmentId, actionId, 'validate')

export const reopenAction = (establishmentId: string, actionId: string) =>
  postActionCommand(establishmentId, actionId, 'reopen')

export const cancelAction = (establishmentId: string, actionId: string) =>
  postActionCommand(establishmentId, actionId, 'cancel')

export async function reassignAction(
  establishmentId: string,
  actionId: string,
  assignedTo: string,
): Promise<ActionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/actions/{action_id}/reassign/', {
        params: actionPathParams(establishmentId, actionId),
        body: { assigned_to: assignedTo },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertActionData<ActionDetail>(result)
}

export async function updateActionDueAt(
  establishmentId: string,
  actionId: string,
  dueAt: string,
): Promise<ActionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PATCH('/api/v1/establishments/{establishment_id}/actions/{action_id}/due-at/', {
        params: actionPathParams(establishmentId, actionId),
        body: { due_at: dueAt },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertActionData<ActionDetail>(result)
}

export async function searchEstablishmentUsers(
  establishmentId: string,
  query: string,
  options: EstablishmentUserSearchOptions = {},
): Promise<ScopedUserSearchResult[]> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/users/search/', {
        params: {
          path: { establishment_id: establishmentId },
          query: {
            q: query,
            ...(options.businessUnitId
              ? { business_unit_id: options.businessUnitId }
              : {}),
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertActionData<ScopedUserSearchResult[]>(result)
}
