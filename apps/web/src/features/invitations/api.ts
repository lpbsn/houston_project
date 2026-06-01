import { apiClient } from '@/api/client'
import { queryClient } from '@/lib/query-client'

import { bootstrapQueryKey } from '@/features/auth/api'
import { ensureCsrfToken } from '@/features/auth/csrf'
import { clearAccessToken, setAccessToken } from '@/features/auth/session'
import type { DirectorInvitationAcceptResponse } from '@/features/invitations/types'
import type { BootstrapResponse } from '@/features/auth/types'

class InvitationAcceptApiError extends Error {
  status: number
  code: string | null

  constructor(message: string, status: number, code: string | null = null) {
    super(message)
    this.name = 'InvitationAcceptApiError'
    this.status = status
    this.code = code
  }
}

function getErrorDetail(error: unknown) {
  if (typeof error !== 'object' || !error) {
    return null
  }

  if ('detail' in error && typeof (error as { detail?: unknown }).detail === 'string') {
    return (error as { detail: string }).detail
  }

  return null
}

function getErrorCode(error: unknown) {
  if (typeof error !== 'object' || !error || !('code' in error)) {
    return null
  }

  const code = (error as { code?: unknown }).code
  return typeof code === 'string' ? code : null
}

function toBootstrapResponse(payload: DirectorInvitationAcceptResponse): BootstrapResponse {
  return {
    authenticated: payload.authenticated,
    user: payload.user,
    memberships: payload.memberships,
    active_membership: payload.active_membership,
  }
}

function hydrateBootstrap(payload: DirectorInvitationAcceptResponse) {
  queryClient.setQueryData<BootstrapResponse>(bootstrapQueryKey, toBootstrapResponse(payload))
}

export async function acceptDirectorInvitation(
  token: string,
  input: { password: string; password_confirmation: string },
) {
  clearAccessToken()
  queryClient.removeQueries({ queryKey: bootstrapQueryKey, exact: true })

  const csrfToken = await ensureCsrfToken()
  const { data, error, response } = await apiClient.POST('/api/v1/invitations/{token}/accept/', {
    params: {
      path: { token },
    },
    body: input,
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  if (error || !data) {
    throw new InvitationAcceptApiError(
      getErrorDetail(error) ?? 'Invitation could not be accepted.',
      response.status,
      getErrorCode(error),
    )
  }

  hydrateBootstrap(data)
  setAccessToken(data.access_token)

  return data
}

export { InvitationAcceptApiError }
