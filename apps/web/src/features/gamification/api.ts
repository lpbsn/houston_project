import { apiClient, withAuthRetry } from '@/api/client'
import { parseStandardApiError } from '@/lib/api-errors'

import type { GamificationOverview } from './types'

export const gamificationQueryKeys = {
  all: ['gamification'] as const,
  overview: (establishmentId: string) =>
    ['gamification', 'overview', establishmentId] as const,
}

export class GamificationApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'GamificationApiError'
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

function parseError(response: Response, payload: unknown): GamificationApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new GamificationApiError({ status, detail, code })
}

function assertGamificationData(result: {
  response: Response
  data?: GamificationOverview
  error?: unknown
}): GamificationOverview {
  if (result.response.ok && result.data) {
    return result.data
  }

  throw parseError(result.response, result.error)
}

export async function fetchGamificationOverview(
  establishmentId: string,
): Promise<GamificationOverview> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/gamification/me/', {
        params: {
          path: {
            establishment_id: establishmentId,
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertGamificationData(result)
}
