import { withAuthRetry } from '@/api/client'

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

async function fetchWithAuthRetry(
  input: RequestInfo | URL,
  init: RequestInit,
): Promise<Response> {
  const result = await withAuthRetry(async (token) => {
    const headers = new Headers(init.headers)
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    } else {
      headers.delete('Authorization')
    }
    const response = await fetch(input, { ...init, headers })
    return { response }
  })
  return result.response
}

function parseError(response: Response, payload: unknown): ActionsApiError {
  const body = typeof payload === 'object' && payload !== null ? payload : {}
  const detail =
    'detail' in body && typeof body.detail === 'string'
      ? body.detail
      : 'Une erreur est survenue.'
  const code = 'code' in body && typeof body.code === 'string' ? body.code : null
  return new ActionsApiError({ status: response.status, detail, code })
}

export async function fetchExecutionFeed(
  establishmentId: string,
  viewMode: ExecutionViewMode,
): Promise<ExecutionFeedResponse> {
  const params = new URLSearchParams({ view_mode: viewMode })
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/execution-feed/?${params.toString()}`,
    { method: 'GET' },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as ExecutionFeedResponse
}

export async function fetchActionDetail(
  establishmentId: string,
  actionId: string,
): Promise<ActionDetail> {
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/actions/${actionId}/`,
    { method: 'GET' },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as ActionDetail
}

export async function createAction(
  establishmentId: string,
  body: ActionCreateRequest,
): Promise<ActionDetail> {
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/actions/`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as ActionDetail
}

async function postActionCommand(
  establishmentId: string,
  actionId: string,
  command: string,
): Promise<ActionDetail> {
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/actions/${actionId}/${command}/`,
    { method: 'POST' },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as ActionDetail
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
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/actions/${actionId}/reassign/`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assigned_to: assignedTo }),
    },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as ActionDetail
}

export async function updateActionDueAt(
  establishmentId: string,
  actionId: string,
  dueAt: string,
): Promise<ActionDetail> {
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/actions/${actionId}/due-at/`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ due_at: dueAt }),
    },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as ActionDetail
}

export async function searchEstablishmentUsers(
  establishmentId: string,
  query: string,
): Promise<ScopedUserSearchResult[]> {
  const params = new URLSearchParams({ q: query })
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/users/search/?${params.toString()}`,
    { method: 'GET' },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as ScopedUserSearchResult[]
}
