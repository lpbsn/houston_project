import { apiClient, withAuthRetry } from '@/api/client'

import type {
  DirectorInvitationResponse,
  OrganizationAdminOwnerInvitationRequest,
} from './types'

class OrganizationApiError extends Error {
  status: number
  code: string | null

  constructor(message: string, status: number, code: string | null = null) {
    super(message)
    this.name = 'OrganizationApiError'
    this.status = status
    this.code = code
  }
}

function getErrorDetail(error: unknown): string | null {
  if (!error || typeof error !== 'object') {
    return null
  }
  if ('detail' in error && typeof error.detail === 'string') {
    return error.detail
  }
  return null
}

function getErrorCode(error: unknown): string | null {
  if (!error || typeof error !== 'object') {
    return null
  }
  if ('code' in error && typeof error.code === 'string') {
    return error.code
  }
  return null
}

function buildOrganizationError(response: Response, error: unknown, fallback: string) {
  return new OrganizationApiError(
    getErrorDetail(error) ?? fallback,
    response.status,
    getErrorCode(error),
  )
}

function authHeaders(accessToken: string | null | undefined) {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : undefined
}

export async function inviteOrganizationOwner(
  organizationId: string,
  body: OrganizationAdminOwnerInvitationRequest,
): Promise<DirectorInvitationResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/organizations/{organization_id}/owner-invitations/', {
        params: { path: { organization_id: organizationId } },
        body,
        headers: authHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOrganizationError(
      result.response,
      result.error,
      'Impossible d’inviter ce propriétaire.',
    )
  }

  return result.data
}
