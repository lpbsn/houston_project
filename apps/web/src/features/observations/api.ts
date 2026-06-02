import { apiClient, withAuthRetry } from '@/api/client'

import type {
  ObservationSubmitRequest,
  ObservationSubmitResponse,
  TemporaryUploadResponse,
  TranscriptionResponse,
} from './types'

export const observationsQueryKeys = {
  all: ['observations'] as const,
}

export class ObservationsApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'ObservationsApiError'
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

function parseError(response: Response, payload: unknown): ObservationsApiError {
  const body = typeof payload === 'object' && payload !== null ? payload : {}
  const detail =
    'detail' in body && typeof body.detail === 'string'
      ? body.detail
      : 'Une erreur est survenue.'
  const code = 'code' in body && typeof body.code === 'string' ? body.code : null
  return new ObservationsApiError({ status: response.status, detail, code })
}

export async function uploadTemporaryPhoto(
  establishmentId: string,
  file: File,
  accessToken: string,
): Promise<TemporaryUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(
    `/api/v1/establishments/${establishmentId}/temporary-uploads/`,
    {
      method: 'POST',
      headers: getAuthHeaders(accessToken),
      body: formData,
    },
  )

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }

  return payload as TemporaryUploadResponse
}

export async function deleteTemporaryPhoto(
  establishmentId: string,
  uploadId: string,
  accessToken: string,
): Promise<void> {
  const response = await fetch(
    `/api/v1/establishments/${establishmentId}/temporary-uploads/${uploadId}/`,
    {
      method: 'DELETE',
      headers: getAuthHeaders(accessToken),
    },
  )

  if (response.status === 204) {
    return
  }

  const payload = await response.json().catch(() => ({}))
  throw parseError(response, payload)
}

export async function transcribeAudio(
  establishmentId: string,
  file: Blob,
  fileName: string,
  accessToken: string,
): Promise<TranscriptionResponse> {
  const formData = new FormData()
  formData.append('file', file, fileName)

  const response = await fetch(
    `/api/v1/establishments/${establishmentId}/transcriptions/`,
    {
      method: 'POST',
      headers: getAuthHeaders(accessToken),
      body: formData,
    },
  )

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw parseError(response, payload)
  }

  return payload as TranscriptionResponse
}

export async function submitObservation(
  establishmentId: string,
  body: ObservationSubmitRequest,
): Promise<ObservationSubmitResponse> {
  const result = await withAuthRetry((token) =>
    apiClient.POST('/api/v1/establishments/{establishment_id}/observations/', {
      params: { path: { establishment_id: establishmentId } },
      body,
      headers: getAuthHeaders(token),
    }),
  )

  if (result.response.ok && result.data) {
    return result.data
  }

  throw parseError(result.response, result.error)
}
