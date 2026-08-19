import { apiClient, withAuthRetry } from '@/api/client'

import { parseStandardApiError } from '@/lib/api-errors'

import type { PushDeviceResponse, PushDeviceUpsert } from './types'

export class PushDevicesApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'PushDevicesApiError'
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

function parseError(response: Response, payload: unknown): PushDevicesApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new PushDevicesApiError({ status, detail, code })
}

function assertPushDeviceData<T>(result: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (result.response.ok && result.data) {
    return result.data
  }

  throw parseError(result.response, result.error)
}

export async function upsertPushDevice(input: PushDeviceUpsert): Promise<PushDeviceResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/me/push-devices/', {
        body: input,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertPushDeviceData<PushDeviceResponse>(result)
}

export async function revokePushDevice(deviceId: string): Promise<void> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.DELETE('/api/v1/me/push-devices/{device_id}/', {
        params: {
          path: {
            device_id: deviceId,
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.response.status === 204) {
    return
  }

  throw parseError(result.response, result.error)
}
