import type { components } from '@/api/generated/types'
import { apiClient, withAuthRetry } from '@/api/client'
import { parseStandardApiError } from '@/lib/api-errors'

import { normalizeSignalFeedFilters } from './lib/signal-feed-filters'
import type {
  SignalDetail,
  SignalFeedFilters,
  SignalFeedResponse,
  SignalQualifyRoutingRequest,
  SignalQualifyRoutingResponse,
  SignalViewMode,
} from './types'

export type BusinessUnitTreeResponse = components['schemas']['BusinessUnitTreeResponse']

export type { SignalFeedFilters } from './lib/signal-feed-filters'

export const signalsQueryKeys = {
  all: ['signals'] as const,
  feed: (establishmentId: string, viewMode: SignalViewMode, filters: SignalFeedFilters) =>
    ['signals', 'feed', establishmentId, viewMode, normalizeSignalFeedFilters(filters)] as const,
  detail: (establishmentId: string, signalId: string) =>
    ['signals', 'detail', establishmentId, signalId] as const,
  qualifyRoutingOptions: (establishmentId: string) =>
    ['signals', 'qualify-routing-options', establishmentId] as const,
}

export class SignalsApiError extends Error {
  status: number
  detail: string
  code: string | null
  payload: unknown

  constructor(options: {
    status: number
    detail: string
    code?: string | null
    payload?: unknown
  }) {
    super(options.detail)
    this.name = 'SignalsApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code ?? null
    this.payload = options.payload
  }
}

function getAuthHeaders(accessToken: string | null) {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : undefined
}

function parseError(response: Response, payload: unknown): SignalsApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new SignalsApiError({ status, detail, code, payload })
}

function assertSignalData<T>(result: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (result.response.ok && result.data) {
    return result.data
  }

  throw parseError(result.response, result.error)
}

function buildSignalFeedQuery(
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  options: { cursor?: string; pageSize?: number } = {},
) {
  const normalized = normalizeSignalFeedFilters(filters)

  return {
    view_mode: viewMode,
    ...(normalized.statuses.length > 0 ? { statuses: normalized.statuses.join(',') } : {}),
    ...(normalized.businessUnitIds.length > 0
      ? { business_unit_ids: normalized.businessUnitIds.join(',') }
      : {}),
    ...(normalized.activitySubjectIds.length > 0
      ? { activity_subject_ids: normalized.activitySubjectIds.join(',') }
      : {}),
    ...(normalized.needsQualification ? { needs_qualification: true } : {}),
    ...(options.cursor ? { cursor: options.cursor } : {}),
    ...(options.pageSize ? { page_size: options.pageSize } : {}),
  }
}

function signalPathParams(establishmentId: string, signalId: string) {
  return {
    path: {
      establishment_id: establishmentId,
      signal_id: signalId,
    },
  }
}

export async function fetchSignalFeed(
  establishmentId: string,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  options: { cursor?: string; pageSize?: number } = {},
): Promise<SignalFeedResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/signal-feed/', {
        params: {
          path: { establishment_id: establishmentId },
          query: buildSignalFeedQuery(viewMode, filters, options),
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertSignalData<SignalFeedResponse>(result)
}

export async function fetchSignalDetail(
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/signals/{signal_id}/', {
        params: signalPathParams(establishmentId, signalId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertSignalData<SignalDetail>(result)
}

export async function pinSignal(establishmentId: string, signalId: string): Promise<SignalDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/signals/{signal_id}/pin/', {
        params: signalPathParams(establishmentId, signalId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertSignalData<SignalDetail>(result)
}

export async function unpinSignal(
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/signals/{signal_id}/unpin/', {
        params: signalPathParams(establishmentId, signalId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertSignalData<SignalDetail>(result)
}

export async function cancelSignal(
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/signals/{signal_id}/cancel/', {
        params: signalPathParams(establishmentId, signalId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertSignalData<SignalDetail>(result)
}

export async function resolveSignal(
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/signals/{signal_id}/resolve/', {
        params: signalPathParams(establishmentId, signalId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertSignalData<SignalDetail>(result)
}

export async function markSignalInteresting(
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/signals/{signal_id}/mark-interesting/',
        {
          params: signalPathParams(establishmentId, signalId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertSignalData<SignalDetail>(result)
}

export async function archiveSignal(
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/signals/{signal_id}/archive/',
        {
          params: signalPathParams(establishmentId, signalId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertSignalData<SignalDetail>(result)
}

export async function qualifySignalRouting(
  establishmentId: string,
  signalId: string,
  body: SignalQualifyRoutingRequest,
): Promise<SignalQualifyRoutingResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/signals/{signal_id}/qualify-routing/',
        {
          params: signalPathParams(establishmentId, signalId),
          headers: getAuthHeaders(accessToken),
          body,
        },
      ),
    { refreshable: true },
  )

  return assertSignalData<SignalQualifyRoutingResponse>(result)
}

export async function fetchQualifyRoutingOptions(
  establishmentId: string,
): Promise<BusinessUnitTreeResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET(
        '/api/v1/establishments/{establishment_id}/signals/qualify-routing-options/',
        {
          params: { path: { establishment_id: establishmentId } },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertSignalData<BusinessUnitTreeResponse>(result)
}
