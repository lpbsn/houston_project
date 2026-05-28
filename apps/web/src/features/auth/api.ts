import { apiClient, withAuthRetry } from '@/api/client'
import { queryClient } from '@/lib/query-client'

import { ensureCsrfToken } from './csrf'
import { clearAccessToken, getAccessToken, setAccessToken } from './session'
import type {
  AuthResponse,
  BootstrapResponse,
  EstablishmentMembershipResponse,
  LoginRequest,
  MembershipUpdateRequest,
  ScopedUserSearchResult,
  SwitchEstablishmentRequest,
} from './types'

export const bootstrapQueryKey = ['auth', 'bootstrap'] as const
export const membershipListQueryKey = (establishmentId: string) =>
  ['workspace', 'memberships', establishmentId] as const
export const membershipDetailQueryKey = (establishmentId: string, membershipId: string) =>
  ['workspace', 'memberships', establishmentId, membershipId] as const
export const scopedUserSearchQueryKey = (establishmentId: string, query: string) =>
  ['workspace', 'user-search', establishmentId, query] as const

class AuthApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'AuthApiError'
    this.status = status
  }
}

function getErrorDetail(error: unknown) {
  if (typeof error !== 'object' || !error || !('detail' in error)) {
    return null
  }

  const detail = (error as { detail?: unknown }).detail
  return typeof detail === 'string' ? detail : null
}

function toBootstrapResponse(payload: AuthResponse): BootstrapResponse {
  return {
    authenticated: payload.authenticated,
    user: payload.user,
    memberships: payload.memberships,
    active_membership: payload.active_membership,
  }
}

function hydrateBootstrap(payload: AuthResponse) {
  queryClient.setQueryData<BootstrapResponse>(bootstrapQueryKey, toBootstrapResponse(payload))
}

function buildAuthError(
  response: Response,
  error: unknown,
  fallbackMessage: string,
) {
  return new AuthApiError(getErrorDetail(error) ?? fallbackMessage, response.status)
}

let refreshPromise: Promise<string | null> | null = null
let restorePromise: Promise<string | null> | null = null

export function clearAuthState() {
  clearAccessToken()
  queryClient.removeQueries({ queryKey: bootstrapQueryKey, exact: true })
}

async function executeRefresh() {
  const csrfToken = await ensureCsrfToken()
  const { data, error, response } = await apiClient.POST('/api/v1/auth/refresh/', {
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  if (error || !data) {
    throw buildAuthError(response, error, 'Your session could not be refreshed.')
  }

  hydrateBootstrap(data)
  setAccessToken(data.access_token)

  return data
}

export async function refreshAccessToken() {
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = (async () => {
    try {
      const payload = await executeRefresh()
      return payload.access_token
    } catch {
      clearAuthState()
      return null
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

export async function restoreSession() {
  if (getAccessToken()) {
    return getAccessToken()
  }

  if (restorePromise) {
    return restorePromise
  }

  restorePromise = (async () => {
    try {
      return await refreshAccessToken()
    } finally {
      restorePromise = null
    }
  })()

  return restorePromise
}

export async function login(input: LoginRequest) {
  const csrfToken = await ensureCsrfToken()
  const { data, error, response } = await apiClient.POST('/api/v1/auth/login/', {
    body: input,
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  if (error || !data) {
    throw buildAuthError(response, error, 'Sign-in failed.')
  }

  hydrateBootstrap(data)
  setAccessToken(data.access_token)

  return data
}

export async function logout() {
  const csrfToken = await ensureCsrfToken()
  const { error, response } = await apiClient.POST('/api/v1/auth/logout/', {
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  if (error || response.status !== 204) {
    throw buildAuthError(response, error, 'Sign-out failed.')
  }
}

export async function fetchBootstrap() {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/auth/bootstrap/', {
        headers: accessToken
          ? {
              Authorization: `Bearer ${accessToken}`,
            }
          : undefined,
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildAuthError(result.response, result.error, 'Your session is not available.')
  }

  return result.data
}

export async function switchEstablishment(input: SwitchEstablishmentRequest) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/auth/switch_establishment/', {
        body: input,
        headers: accessToken
          ? {
              Authorization: `Bearer ${accessToken}`,
            }
          : undefined,
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildAuthError(result.response, result.error, 'We could not switch this establishment.')
  }

  queryClient.setQueryData<BootstrapResponse>(bootstrapQueryKey, result.data)
  return result.data
}

export async function listMemberships(establishmentId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/memberships/', {
        params: {
          path: { establishment_id: establishmentId },
        },
        headers: accessToken
          ? {
              Authorization: `Bearer ${accessToken}`,
            }
          : undefined,
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildAuthError(result.response, result.error, 'Memberships could not be loaded.')
  }

  return result.data as EstablishmentMembershipResponse[]
}

export async function getMembership(establishmentId: string, membershipId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/memberships/{membership_id}/', {
        params: {
          path: {
            establishment_id: establishmentId,
            membership_id: membershipId,
          },
        },
        headers: accessToken
          ? {
              Authorization: `Bearer ${accessToken}`,
            }
          : undefined,
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildAuthError(result.response, result.error, 'Membership details are unavailable.')
  }

  return result.data as EstablishmentMembershipResponse
}

export async function updateMembership(
  establishmentId: string,
  membershipId: string,
  input: MembershipUpdateRequest,
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PATCH('/api/v1/establishments/{establishment_id}/memberships/{membership_id}/', {
        params: {
          path: {
            establishment_id: establishmentId,
            membership_id: membershipId,
          },
        },
        body: input,
        headers: accessToken
          ? {
              Authorization: `Bearer ${accessToken}`,
            }
          : undefined,
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildAuthError(result.response, result.error, 'Membership changes were not saved.')
  }

  await queryClient.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true })
  return result.data as EstablishmentMembershipResponse
}

export async function deactivateMembership(establishmentId: string, membershipId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/memberships/{membership_id}/deactivate/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              membership_id: membershipId,
            },
          },
          headers: accessToken
            ? {
                Authorization: `Bearer ${accessToken}`,
              }
            : undefined,
        },
      ),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildAuthError(result.response, result.error, 'This membership could not be deactivated.')
  }

  await queryClient.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true })
  return result.data as EstablishmentMembershipResponse
}

export async function searchUsers(establishmentId: string, query: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/users/search/', {
        params: {
          path: { establishment_id: establishmentId },
          query: { q: query },
        },
        headers: accessToken
          ? {
              Authorization: `Bearer ${accessToken}`,
            }
          : undefined,
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildAuthError(result.response, result.error, 'User search is unavailable.')
  }

  return result.data as ScopedUserSearchResult[]
}

export { AuthApiError }
