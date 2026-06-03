import { withAuthRetry } from '@/api/client'

import type { SignalDetail, SignalFeedResponse, SignalViewMode } from './types'

export const signalsQueryKeys = {
  all: ['signals'] as const,
  feed: (establishmentId: string, viewMode: SignalViewMode) =>
    ['signals', 'feed', establishmentId, viewMode] as const,
  detail: (establishmentId: string, signalId: string) =>
    ['signals', 'detail', establishmentId, signalId] as const,
}

export class SignalsApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'SignalsApiError'
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

function parseError(response: Response, payload: unknown): SignalsApiError {
  const body = typeof payload === 'object' && payload !== null ? payload : {}
  const detail =
    'detail' in body && typeof body.detail === 'string'
      ? body.detail
      : 'Une erreur est survenue.'
  const code = 'code' in body && typeof body.code === 'string' ? body.code : null
  return new SignalsApiError({ status: response.status, detail, code })
}

export async function fetchSignalFeed(
  establishmentId: string,
  viewMode: SignalViewMode,
): Promise<SignalFeedResponse> {
  const params = new URLSearchParams({ view_mode: viewMode })
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/signal-feed/?${params.toString()}`,
    { method: 'GET' },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as SignalFeedResponse
}

export async function fetchSignalDetail(
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/signals/${signalId}/`,
    { method: 'GET' },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as SignalDetail
}

export async function pinSignal(establishmentId: string, signalId: string): Promise<SignalDetail> {
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/signals/${signalId}/pin/`,
    { method: 'POST' },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as SignalDetail
}

export async function unpinSignal(
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/signals/${signalId}/unpin/`,
    { method: 'POST' },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as SignalDetail
}

export async function setSignalUrgency(
  establishmentId: string,
  signalId: string,
  urgency: 'normal' | 'high',
): Promise<SignalDetail> {
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/signals/${signalId}/urgency/`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urgency }),
    },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as SignalDetail
}

export async function cancelSignal(
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/signals/${signalId}/cancel/`,
    { method: 'POST' },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as SignalDetail
}

export async function resolveSignal(
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/signals/${signalId}/resolve/`,
    { method: 'POST' },
  )
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }
  return payload as SignalDetail
}
