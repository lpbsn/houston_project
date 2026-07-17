import type { QueryClient } from '@tanstack/react-query'

import { apiClient, withAuthRetry } from '@/api/client'
import { clearAllMixedSubmissionIntents } from '@/features/action-plans/lib/action-plan-mixed-submission-intent'
import { queryClient } from '@/lib/query-client'
import {
  clearAuthenticatedQueryCache,
  purgeNonAuthQueries,
} from '@/lib/query-invalidation'

import { ensureCsrfToken } from './csrf'
import { clearAccessToken, getAccessToken, setAccessToken } from './session'
import type {
  AuthResponse,
  BootstrapResponse,
  EstablishmentMembershipResponse,
  LoginRequest,
  MembershipUpdateRequest,
  MembershipInvitationRequest,
  RegistrationOwnerValidateRequest,
  RegistrationRequest,
  RegistrationResponse,
  SwitchEstablishmentRequest,
  WorkspaceSummaryResponse,
  BusinessUnitTreeResponse,
} from './types'

export const bootstrapQueryKey = ['auth', 'bootstrap'] as const
export const membershipsQueryKeyRoot = ['workspace', 'memberships'] as const
export const membershipListQueryKey = (establishmentId: string) =>
  [...membershipsQueryKeyRoot, establishmentId] as const
export const membershipDetailQueryKey = (establishmentId: string, membershipId: string) =>
  [...membershipsQueryKeyRoot, establishmentId, membershipId] as const
export const workspaceSummaryQueryKey = (establishmentId: string) =>
  ['workspace', 'summary', establishmentId] as const

class AuthApiError extends Error {
  status: number
  code: string | null

  constructor(message: string, status: number, code: string | null = null) {
    super(message)
    this.name = 'AuthApiError'
    this.status = status
    this.code = code
  }
}

/** Best-effort: never rejects; attempts every planned invalidation. */
async function settleQueryInvalidations(invalidations: Array<Promise<unknown>>) {
  await Promise.allSettled(invalidations)
}

/**
 * Invalidate all membership list/detail caches (org-owner fan-out safe).
 * Best-effort: absorbs errors so callers can fire-and-forget after successful writes.
 */
export async function invalidateMembershipWorkspaceQueries(options?: {
  includeBootstrap?: boolean
  queryClient?: QueryClient
}) {
  const client = options?.queryClient ?? queryClient
  const invalidations = [client.invalidateQueries({ queryKey: membershipsQueryKeyRoot })]
  if (options?.includeBootstrap !== false) {
    invalidations.push(client.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true }))
  }
  await settleQueryInvalidations(invalidations)
}

/** Best-effort list + detail invalidation for a single establishment membership. */
export async function invalidateMembershipListAndDetailQueries(
  establishmentId: string,
  membershipId: string,
  client: QueryClient = queryClient,
) {
  await settleQueryInvalidations([
    client.invalidateQueries({ queryKey: membershipListQueryKey(establishmentId) }),
    client.invalidateQueries({
      queryKey: membershipDetailQueryKey(establishmentId, membershipId),
    }),
  ])
}

/** Best-effort list + workspace summary invalidation. */
export async function invalidateMembershipListAndWorkspaceSummaryQueries(
  establishmentId: string,
  client: QueryClient = queryClient,
) {
  await settleQueryInvalidations([
    client.invalidateQueries({ queryKey: membershipListQueryKey(establishmentId) }),
    client.invalidateQueries({ queryKey: workspaceSummaryQueryKey(establishmentId) }),
  ])
}

/** Best-effort membership list invalidation (e.g. after invite). */
export async function invalidateMembershipListQueries(
  establishmentId: string,
  client: QueryClient = queryClient,
) {
  await settleQueryInvalidations([
    client.invalidateQueries({ queryKey: membershipListQueryKey(establishmentId) }),
  ])
}

/** Synchronously patch detail + list caches from a membership API response. */
export function patchMembershipCaches(
  establishmentId: string,
  membership: EstablishmentMembershipResponse,
  client: QueryClient = queryClient,
) {
  client.setQueryData(membershipDetailQueryKey(establishmentId, membership.id), membership)
  client.setQueryData(
    membershipListQueryKey(establishmentId),
    (current: EstablishmentMembershipResponse[] | undefined) => {
      if (!current) {
        return current
      }
      return current.map((item) => (item.id === membership.id ? membership : item))
    },
  )
}

/**
 * After a successful membership write: patch list+detail, then best-effort invalidations.
 * Owner path fans out via memberships root + bootstrap; optional workspace summary on any role.
 */
export function commitMembershipWriteCache(
  establishmentId: string,
  membership: EstablishmentMembershipResponse,
  client: QueryClient = queryClient,
  options?: { includeWorkspaceSummary?: boolean },
) {
  patchMembershipCaches(establishmentId, membership, client)

  const invalidations: Array<Promise<unknown>> = []
  if (membership.role === 'owner') {
    invalidations.push(client.invalidateQueries({ queryKey: membershipsQueryKeyRoot }))
    invalidations.push(client.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true }))
  } else {
    invalidations.push(client.invalidateQueries({ queryKey: membershipListQueryKey(establishmentId) }))
    invalidations.push(
      client.invalidateQueries({
        queryKey: membershipDetailQueryKey(establishmentId, membership.id),
      }),
    )
  }
  if (options?.includeWorkspaceSummary) {
    invalidations.push(
      client.invalidateQueries({ queryKey: workspaceSummaryQueryKey(establishmentId) }),
    )
  }
  void settleQueryInvalidations(invalidations)
}

const REGISTRATION_STEP1_FIELDS = new Set([
  'invite_code',
  'first_name',
  'last_name',
  'email',
  'password',
  'password_confirmation',
])

function getErrorDetail(error: unknown) {
  if (typeof error !== 'object' || !error || !('detail' in error)) {
    return null
  }

  const detail = (error as { detail?: unknown }).detail
  return typeof detail === 'string' ? detail : null
}

function getErrorCode(error: unknown) {
  if (typeof error !== 'object' || !error || !('code' in error)) {
    return null
  }

  const code = (error as { code?: unknown }).code
  return typeof code === 'string' ? code : null
}

function parseRegistrationFieldErrors(
  error: unknown,
): Partial<Record<string, string[]>> | undefined {
  if (typeof error !== 'object' || !error) {
    return undefined
  }

  const fieldErrors: Partial<Record<string, string[]>> = {}

  for (const [key, value] of Object.entries(error)) {
    if (key === 'detail' || key === 'code') {
      continue
    }

    if (Array.isArray(value) && value.every((item) => typeof item === 'string')) {
      fieldErrors[key] = value
      continue
    }

    if (typeof value === 'string') {
      fieldErrors[key] = [value]
    }
  }

  return Object.keys(fieldErrors).length > 0 ? fieldErrors : undefined
}

export class RegistrationValidationError extends Error {
  status: number
  code: string | null
  fieldErrors?: Partial<Record<string, string[]>>

  constructor(
    message: string,
    status: number,
    options?: { code?: string | null; fieldErrors?: Partial<Record<string, string[]>> },
  ) {
    super(message)
    this.name = 'RegistrationValidationError'
    this.status = status
    this.code = options?.code ?? null
    this.fieldErrors = options?.fieldErrors
  }
}

function buildRegistrationValidationError(
  response: Response,
  error: unknown,
  fallbackMessage: string,
) {
  const code = getErrorCode(error)
  const fieldErrors = parseRegistrationFieldErrors(error)
  const detail = getErrorDetail(error)

  let message = fallbackMessage

  if (code === 'invalid_invite_code') {
    message = detail ?? 'Invalid invitation code.'
  } else if (code === 'duplicate_email') {
    message = detail ?? 'An account with this email already exists.'
  } else if (fieldErrors?.password?.length) {
    message = fieldErrors.password.join(' ')
  } else if (fieldErrors?.password_confirmation?.length) {
    message = fieldErrors.password_confirmation[0] ?? message
  } else if (fieldErrors?.invite_code?.length) {
    message = fieldErrors.invite_code[0] ?? message
  } else if (fieldErrors?.email?.length) {
    message = fieldErrors.email[0] ?? message
  } else if (detail) {
    message = detail
  }

  return new RegistrationValidationError(message, response.status, { code, fieldErrors })
}

export function isRegistrationStep1Error(error: unknown) {
  if (!(error instanceof RegistrationValidationError)) {
    return false
  }

  if (error.code === 'invalid_invite_code' || error.code === 'duplicate_email') {
    return true
  }

  if (!error.fieldErrors) {
    return false
  }

  return Object.keys(error.fieldErrors).some((field) => REGISTRATION_STEP1_FIELDS.has(field))
}

function toBootstrapResponse(payload: AuthResponse): BootstrapResponse {
  return {
    authenticated: payload.authenticated,
    user: payload.user,
    memberships: payload.memberships,
    active_membership: payload.active_membership,
    pending_onboarding_memberships: payload.pending_onboarding_memberships ?? [],
    permission_hints: payload.permission_hints,
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
  return new AuthApiError(
    getErrorDetail(error) ?? fallbackMessage,
    response.status,
    getErrorCode(error),
  )
}

let refreshPromise: Promise<string | null> | null = null
let restorePromise: Promise<string | null> | null = null

export function clearAuthState() {
  clearAccessToken()
  clearAllMixedSubmissionIntents()
  clearAuthenticatedQueryCache(queryClient)
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

  purgeNonAuthQueries(queryClient)
  clearAllMixedSubmissionIntents()
  hydrateBootstrap(data)
  setAccessToken(data.access_token)

  return data
}

export async function validateRegistrationOwner(input: RegistrationOwnerValidateRequest) {
  const csrfToken = await ensureCsrfToken()
  const { error, response } = await apiClient.POST('/api/v1/auth/register/validate-owner/', {
    body: input,
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  if (response.status === 204) {
    return
  }

  throw buildRegistrationValidationError(
    response,
    error,
    'Owner details could not be validated.',
  )
}

export async function registerOnboarding(input: RegistrationRequest) {
  const csrfToken = await ensureCsrfToken()
  const { data, error, response } = await apiClient.POST('/api/v1/auth/register/', {
    body: input,
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  if (error || !data) {
    throw buildRegistrationValidationError(
      response,
      error,
      'Registration could not be completed.',
    )
  }

  purgeNonAuthQueries(queryClient)
  clearAllMixedSubmissionIntents()
  hydrateBootstrap(data)
  setAccessToken(data.access_token)

  return data as RegistrationResponse
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

  purgeNonAuthQueries(queryClient)
  clearAllMixedSubmissionIntents()
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

  return result.data as EstablishmentMembershipResponse
}

export async function activateMembership(establishmentId: string, membershipId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/memberships/{membership_id}/activate/',
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
    throw buildAuthError(result.response, result.error, 'This membership could not be activated.')
  }

  return result.data as EstablishmentMembershipResponse
}

export type UserProfileUpdateRequest = {
  first_name?: string
  last_name?: string
  email?: string | null
}

export async function updateUserProfile(input: UserProfileUpdateRequest) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PATCH('/api/v1/auth/me/', {
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
    throw buildAuthError(result.response, result.error, 'Profile changes were not saved.')
  }

  queryClient.setQueryData<BootstrapResponse>(bootstrapQueryKey, result.data)
  return result.data
}

export async function getWorkspaceSummary(establishmentId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/workspace-summary/', {
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
    throw buildAuthError(result.response, result.error, 'Establishment summary is unavailable.')
  }

  return result.data as WorkspaceSummaryResponse
}

export async function inviteMembership(
  establishmentId: string,
  input: MembershipInvitationRequest,
) {
  const csrfToken = await ensureCsrfToken()
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/membership-invitations/', {
        params: {
          path: { establishment_id: establishmentId },
        },
        body: input,
        credentials: 'include',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'X-CSRFToken': csrfToken,
        },
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildAuthError(result.response, result.error, 'Invitation could not be created.')
  }

  return result.data
}

export const businessUnitTreeQueryKey = (establishmentId: string) =>
  ['workspace', 'business-units', establishmentId] as const

export type { BusinessUnitTreeResponse }

export async function fetchBusinessUnitTree(
  establishmentId: string,
  options?: { includeInactive?: boolean },
): Promise<BusinessUnitTreeResponse> {
  const csrfToken = await ensureCsrfToken()
  let path = `/api/v1/establishments/${establishmentId}/business-units/`
  if (options?.includeInactive) {
    path += '?include_inactive=true'
  }
  const result = await withAuthRetry(
    (accessToken) =>
      fetch(path, {
        credentials: 'include',
        headers: {
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          'X-CSRFToken': csrfToken,
        },
      }).then(async (response) => ({
        response,
        data: response.ok ? ((await response.json()) as BusinessUnitTreeResponse) : null,
      })),
    { refreshable: true },
  )

  if (!result.response.ok || !result.data) {
    throw new AuthApiError('Business unit tree could not be loaded.', result.response.status)
  }

  return result.data
}

export { AuthApiError }
