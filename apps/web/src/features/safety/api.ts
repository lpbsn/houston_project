import { apiClient, withAuthRetry } from '@/api/client'

import { parseStandardApiError } from '@/lib/api-errors'

export class SafetyApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'SafetyApiError'
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

function parseError(response: Response, payload: unknown): SafetyApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new SafetyApiError({ status, detail, code })
}

export type ContentReportKind = 'observation' | 'comment' | 'chat_message' | 'user'

export async function blockMembership(establishmentId: string, membershipId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/memberships/{membership_id}/block/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              membership_id: membershipId,
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  if (!result.response.ok) {
    throw parseError(result.response, result.error)
  }
}

export async function createContentReport(
  establishmentId: string,
  input: {
    content_kind: ContentReportKind
    reason: string
    target_membership_id?: string
    content_id?: string
  },
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/content-reports/', {
        params: {
          path: {
            establishment_id: establishmentId,
          },
        },
        body: input,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (!result.response.ok || !result.data) {
    throw parseError(result.response, result.error)
  }
  return result.data
}
