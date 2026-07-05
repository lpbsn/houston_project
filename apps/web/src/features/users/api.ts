import { apiClient, withAuthRetry } from '@/api/client'

import { parseStandardApiError } from '@/lib/api-errors'

import type { ScopedUserSearchResult } from './types'

export const establishmentUserSearchQueryKey = (
  establishmentId: string,
  query: string,
  businessUnitId?: string,
) => ['users', 'search', establishmentId, query, businessUnitId ?? null] as const

export type EstablishmentUserSearchOptions = {
  businessUnitId?: string
}

export class UsersApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'UsersApiError'
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

function parseError(response: Response, payload: unknown): UsersApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new UsersApiError({ status, detail, code })
}

function assertUserData<T>(result: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (result.response.ok && result.data) {
    return result.data
  }

  throw parseError(result.response, result.error)
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

  return assertUserData<ScopedUserSearchResult[]>(result)
}
