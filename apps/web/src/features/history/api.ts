import type { components } from '@/api/generated/types'
import { apiClient, withAuthRetry } from '@/api/client'
import { parseStandardApiError } from '@/lib/api-errors'

export type SignalHistoryResponse = components['schemas']['SignalHistoryResponse']
export type ExecutionHistoryResponse = components['schemas']['ExecutionHistoryResponse']
export type SignalHistoryItem = components['schemas']['SignalHistoryItem']
export type ExecutionHistoryItem = components['schemas']['ExecutionHistoryItem']
export type HistoryViewMode = 'personal' | 'general'
export type HistoryPeriod = '7' | '30' | '90' | 'custom' | 'all'
export type HistoryKind = 'signals' | 'executions'

export type HistoryQuery = {
  viewMode: HistoryViewMode
  period: HistoryPeriod
  status: string
  from?: string
  to?: string
  cursor?: string
  pageSize?: number
}

export class HistoryApiError extends Error {
  status: number
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'HistoryApiError'
    this.status = options.status
    this.code = options.code ?? null
  }
}

function authHeaders(accessToken: string | null) {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined
}

function historyQuery<Status extends string>(query: HistoryQuery, statuses: readonly Status[]) {
  const status = (statuses as readonly string[]).includes(query.status) ? query.status : 'all'
  return {
    view_mode: query.viewMode,
    period: query.period,
    status: status as Status | 'all',
    ...(query.from ? { from: query.from } : {}),
    ...(query.to ? { to: query.to } : {}),
    ...(query.cursor ? { cursor: query.cursor } : {}),
    ...(query.pageSize ? { page_size: query.pageSize } : {}),
  }
}

async function readHistory<T>(
  result: { data?: T; error?: unknown; response: Response },
): Promise<T> {
  if (result.response.ok && result.data) {
    return result.data
  }
  const parsed = parseStandardApiError(
    result.response,
    result.error,
    "Impossible de charger l'historique.",
  )
  throw new HistoryApiError(parsed)
}

export async function fetchSignalHistory(
  establishmentId: string,
  query: HistoryQuery,
): Promise<SignalHistoryResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/history/signals/', {
        params: {
          path: { establishment_id: establishmentId },
          query: historyQuery(query, ['resolved', 'canceled'] as const),
        },
        headers: authHeaders(accessToken),
      }),
    { refreshable: true },
  )
  return readHistory(result)
}

export async function fetchCrossSignalHistory(query: HistoryQuery): Promise<SignalHistoryResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/cross/history/signals/', {
        params: { query: historyQuery(query, ['resolved', 'canceled'] as const) },
        headers: authHeaders(accessToken),
      }),
    { refreshable: true },
  )
  return readHistory(result)
}

export async function fetchExecutionHistory(
  establishmentId: string,
  query: HistoryQuery,
): Promise<ExecutionHistoryResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/history/executions/', {
        params: {
          path: { establishment_id: establishmentId },
          query: historyQuery(query, ['done', 'canceled'] as const),
        },
        headers: authHeaders(accessToken),
      }),
    { refreshable: true },
  )
  return readHistory(result)
}

export async function fetchCrossExecutionHistory(
  query: HistoryQuery,
): Promise<ExecutionHistoryResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/cross/history/executions/', {
        params: { query: historyQuery(query, ['done', 'canceled'] as const) },
        headers: authHeaders(accessToken),
      }),
    { refreshable: true },
  )
  return readHistory(result)
}
