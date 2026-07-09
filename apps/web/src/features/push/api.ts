import { apiClient, withAuthRetry } from '@/api/client'

import { parseStandardApiError } from '@/lib/api-errors'

import type { VapidPublicKey, WebPushSubscriptionResponse, WebPushSubscriptionUpsert } from './types'

export class PushApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'PushApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code ?? null
  }
}

function parseError(response: Response, payload: unknown): PushApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new PushApiError({ status, detail, code })
}

function assertPushData<T>(result: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (result.response.ok && result.data) {
    return result.data
  }

  throw parseError(result.response, result.error)
}

function getAuthHeaders(accessToken: string | null) {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : undefined
}

export async function fetchVapidPublicKey(): Promise<VapidPublicKey> {
  const result = await apiClient.GET('/api/v1/push/vapid-public-key/')

  return assertPushData<VapidPublicKey>(result)
}

export async function upsertWebPushSubscription(
  input: WebPushSubscriptionUpsert,
): Promise<WebPushSubscriptionResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/me/web-push-subscriptions/', {
        body: input,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertPushData<WebPushSubscriptionResponse>(result)
}

export async function deleteWebPushSubscription(subscriptionId: string): Promise<void> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.DELETE('/api/v1/me/web-push-subscriptions/{subscription_id}/', {
        params: {
          path: {
            subscription_id: subscriptionId,
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.response.ok) {
    return
  }

  throw parseError(result.response, result.error)
}
