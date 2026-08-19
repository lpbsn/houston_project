import type { QueryClient } from '@tanstack/react-query'

import { apiClient, withAuthRetry } from '@/api/client'
import { clearAllPlanningSubmissionIntents } from '@/features/action-plans/lib/action-plan-planning-submission-intent'
import { clearObservationProcessingTrackerOnLogout } from '@/features/observations/lib/observation-processing-tracker-store'
import { clearRegistrationSessionSnapshot } from '@/features/onboarding/lib/registration-session-storage'
import { runNativePushBeforeLogout } from '@/lib/native-push-session'
import { queryClient } from '@/lib/query-client'
import {
  clearAuthenticatedQueryCache,
  purgeNonAuthQueries,
} from '@/lib/query-invalidation'
import { clearSuccessToasts } from '@/lib/success-toast'

import { clearCsrfTokenCache, ensureCsrfToken } from './csrf'
import {
  clearPersistedRefreshToken,
  getRefreshTokenTransport,
  persistRefreshFromAuthResponse,
  prepareLogoutTransport,
  prepareRefreshTransport,
  prepareSessionCreationTransport,
  type PreparedAuthTransport,
} from './refresh-token-transport'
import { clearAccessToken, getAccessToken, setAccessToken } from './session'
import type {
  AuthResponse,
  BootstrapResponse,
  DirectorInvitationAcceptInput,
  EstablishmentCreateRequest,
  EstablishmentCreateResponse,
  EstablishmentMembershipDetailResponse,
  EstablishmentMembershipResponse,
  LoginRequest,
  MembershipUpdateRequest,
  MembershipInvitationRequest,
  MembershipReinviteResponse,
  RegistrationOwnerValidateRequest,
  RegistrationRequest,
  RegistrationResponse,
  SwitchEstablishmentRequest,
  BusinessUnitTreeResponse,
} from './types'

export const bootstrapQueryKey = ['auth', 'bootstrap'] as const
export const membershipsQueryKeyRoot = ['workspace', 'memberships'] as const
export const membershipListQueryKey = (establishmentId: string) =>
  [...membershipsQueryKeyRoot, establishmentId] as const
export const membershipDetailQueryKey = (establishmentId: string, membershipId: string) =>
  [...membershipsQueryKeyRoot, establishmentId, membershipId] as const

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

class StaleAuthOperationError extends Error {}

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
  membership: EstablishmentMembershipResponse | EstablishmentMembershipDetailResponse,
  client: QueryClient = queryClient,
) {
  client.setQueryData(membershipDetailQueryKey(establishmentId, membership.id), membership)
  client.setQueryData(
    membershipListQueryKey(establishmentId),
    (current: EstablishmentMembershipResponse[] | undefined) => {
      if (!current) {
        return current
      }
      return current.map((item) =>
        item.id === membership.id ? (membership as EstablishmentMembershipResponse) : item,
      )
    },
  )
}

/**
 * After a successful membership write: patch list+detail, then best-effort invalidations.
 * Owner path fans out via memberships root + bootstrap.
 */
export function commitMembershipWriteCache(
  establishmentId: string,
  membership: EstablishmentMembershipResponse | EstablishmentMembershipDetailResponse,
  client: QueryClient = queryClient,
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
let authGeneration = 0
let authInvalidationGeneration = 0
let sessionEpoch = 0
let sessionReplacementDepth = 0
let sessionReplacementIdle: Promise<void> = Promise.resolve()
let resolveSessionReplacementIdle: (() => void) | null = null
let cookieSessionReplacementQueue: Promise<void> = Promise.resolve()
let bodyAuthCommitQueue: Promise<void> = Promise.resolve()

function clearVolatileAuthState(options?: { bumpInvalidation?: boolean }) {
  authGeneration += 1
  sessionEpoch += 1
  if (options?.bumpInvalidation !== false) {
    authInvalidationGeneration += 1
  }
  clearCsrfTokenCache()
  clearAccessToken()
  clearAllPlanningSubmissionIntents()
  clearObservationProcessingTrackerOnLogout()
  clearRegistrationSessionSnapshot()
  clearSuccessToasts()
  clearAuthenticatedQueryCache(queryClient)
}

function clearPersistedRefreshTokenBestEffort() {
  if (getRefreshTokenTransport() === 'body') {
    void enqueueAuthOperation(
      bodyAuthCommitQueue,
      (next) => {
        bodyAuthCommitQueue = next
      },
      clearPersistedRefreshToken,
    ).catch(() => undefined)
  }
}

export function clearAuthState() {
  clearVolatileAuthState()
  clearPersistedRefreshTokenBestEffort()
}

function buildTransportHeaders(prepared: PreparedAuthTransport, accessToken?: string | null) {
  const headers: Record<string, string> = {}
  if (prepared.csrfToken) {
    headers['X-CSRFToken'] = prepared.csrfToken
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }
  return Object.keys(headers).length > 0 ? headers : undefined
}

type AuthEnvelope = AuthResponse & {
  refresh_token?: string
  refresh_token_expires_at?: string
}

function enqueueAuthOperation<T>(
  queue: Promise<void>,
  updateQueue: (next: Promise<void>) => void,
  operation: () => Promise<T>,
) {
  const result = queue.then(operation, operation)
  updateQueue(result.then(() => undefined, () => undefined))
  return result
}

function beginSessionReplacement() {
  if (sessionReplacementDepth === 0) {
    sessionReplacementIdle = new Promise((resolve) => {
      resolveSessionReplacementIdle = resolve
    })
  }
  sessionReplacementDepth += 1
  authGeneration += 1
  return authGeneration
}

function endSessionReplacement() {
  sessionReplacementDepth -= 1
  if (sessionReplacementDepth === 0) {
    resolveSessionReplacementIdle?.()
    resolveSessionReplacementIdle = null
    sessionReplacementIdle = Promise.resolve()
  }
}

async function runSessionReplacement<T>(
  operation: (prepared: PreparedAuthTransport, generation: number) => Promise<T>,
) {
  if (getRefreshTokenTransport() === 'body') {
    const generation = beginSessionReplacement()
    try {
      const prepared = await prepareSessionCreationTransport()
      return await operation(prepared, generation)
    } finally {
      endSessionReplacement()
    }
  }

  const invalidationGeneration = authInvalidationGeneration
  const prepared = await prepareSessionCreationTransport()
  return enqueueAuthOperation(
    cookieSessionReplacementQueue,
    (next) => {
      cookieSessionReplacementQueue = next
    },
    async () => {
      if (invalidationGeneration !== authInvalidationGeneration) {
        throw new StaleAuthOperationError('The authenticated session is no longer current.')
      }
      const generation = beginSessionReplacement()
      try {
        return await operation(prepared, generation)
      } finally {
        endSessionReplacement()
      }
    },
  )
}

async function revokeTransientSession(
  payload: AuthEnvelope,
  prepared: PreparedAuthTransport,
) {
  try {
    await apiClient.POST('/api/v1/auth/logout/', {
      body: {
        refresh_token_transport: prepared.transport,
        ...(prepared.transport === 'body' && payload.refresh_token
          ? { refresh_token: payload.refresh_token }
          : {}),
      },
      credentials: prepared.credentials,
      headers: buildTransportHeaders(prepared, payload.access_token),
    })
  } catch {
    // Best-effort cleanup: local state must still fail closed.
  }
}

async function rejectStaleAuthEnvelope(
  payload: AuthEnvelope,
  prepared: PreparedAuthTransport,
  options: { persistedBodyRefresh?: boolean } = {},
): Promise<never> {
  await revokeTransientSession(payload, prepared)
  if (prepared.transport === 'body' && options.persistedBodyRefresh) {
    await clearPersistedRefreshToken().catch(() => undefined)
  }
  throw new StaleAuthOperationError('The authenticated session is no longer current.')
}

function isStaleAuthCommit(
  generation: number,
  expectedEpoch: number | undefined,
) {
  if (expectedEpoch !== undefined) {
    return expectedEpoch !== sessionEpoch
  }
  return generation !== authGeneration
}

async function commitCurrentAuthEnvelope(
  payload: AuthEnvelope,
  prepared: PreparedAuthTransport,
  generation: number,
  options: { purgeNonAuth?: boolean; expectedEpoch?: number },
) {
  if (isStaleAuthCommit(generation, options.expectedEpoch)) {
    return rejectStaleAuthEnvelope(payload, prepared)
  }

  try {
    await persistRefreshFromAuthResponse(payload)
  } catch (error) {
    clearVolatileAuthState()
    await Promise.allSettled([
      revokeTransientSession(payload, prepared),
      clearPersistedRefreshToken(),
    ])
    throw new Error('The authenticated session could not be persisted.', { cause: error })
  }

  if (isStaleAuthCommit(generation, options.expectedEpoch)) {
    return rejectStaleAuthEnvelope(payload, prepared, {
      persistedBodyRefresh: prepared.transport === 'body',
    })
  }

  if (options.purgeNonAuth) {
    purgeNonAuthQueries(queryClient)
    clearAllPlanningSubmissionIntents()
    clearSuccessToasts()
  }
  setAccessToken(payload.access_token)
  hydrateBootstrap(payload)
  sessionEpoch += 1
}

async function commitAuthEnvelope(
  payload: AuthEnvelope,
  prepared: PreparedAuthTransport,
  options: { expectedGeneration?: number; expectedEpoch?: number; purgeNonAuth?: boolean } = {},
) {
  const generation = options.expectedGeneration ?? authGeneration
  if (prepared.transport === 'body') {
    return enqueueAuthOperation(
      bodyAuthCommitQueue,
      (next) => {
        bodyAuthCommitQueue = next
      },
      () => commitCurrentAuthEnvelope(payload, prepared, generation, options),
    )
  }
  return commitCurrentAuthEnvelope(payload, prepared, generation, options)
}

function captureAuthGeneration() {
  return authGeneration
}

function captureSessionEpoch() {
  return sessionEpoch
}

async function performRefresh() {
  const generation = captureAuthGeneration()
  const epoch = captureSessionEpoch()
  const bodyTransport = getRefreshTokenTransport() === 'body'
  try {
    const prepared = await prepareRefreshTransport()
    const { data, error, response } = await apiClient.POST('/api/v1/auth/refresh/', {
      body: {
        refresh_token_transport: prepared.transport,
        ...(prepared.refreshToken ? { refresh_token: prepared.refreshToken } : {}),
      },
      credentials: prepared.credentials,
      headers: buildTransportHeaders(prepared),
    })

    if (error || !data) {
      throw buildAuthError(response, error, 'Your session could not be refreshed.')
    }

    if (bodyTransport) {
      await sessionReplacementIdle
    }

    await commitAuthEnvelope(data, prepared, {
      expectedGeneration: generation,
      ...(bodyTransport ? { expectedEpoch: epoch } : {}),
    })
    return data
  } catch (error) {
    if (error instanceof StaleAuthOperationError) {
      throw error
    }
    if (bodyTransport) {
      await sessionReplacementIdle
      if (epoch !== sessionEpoch) {
        throw new StaleAuthOperationError('The authenticated session is no longer current.')
      }
    } else if (generation !== authGeneration) {
      throw new StaleAuthOperationError('The authenticated session is no longer current.')
    }
    clearVolatileAuthState({ bumpInvalidation: false })
    clearPersistedRefreshTokenBestEffort()
    throw new StaleAuthOperationError('The authenticated session is no longer current.')
  }
}

async function executeRefresh() {
  if (getRefreshTokenTransport() === 'cookie') {
    const invalidationGeneration = authInvalidationGeneration
    return enqueueAuthOperation(
      cookieSessionReplacementQueue,
      (next) => {
        cookieSessionReplacementQueue = next
      },
      async () => {
        if (invalidationGeneration !== authInvalidationGeneration) {
          throw new StaleAuthOperationError('The authenticated session is no longer current.')
        }
        return performRefresh()
      },
    )
  }

  await sessionReplacementIdle
  return performRefresh()
}

export async function refreshAccessToken() {
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = (async () => {
    try {
      const payload = await executeRefresh()
      return payload.access_token
    } catch (error) {
      if (!(error instanceof StaleAuthOperationError)) {
        clearVolatileAuthState({ bumpInvalidation: false })
        clearPersistedRefreshTokenBestEffort()
      }
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
  return runSessionReplacement(async (prepared, generation) => {
    const { data, error, response } = await apiClient.POST('/api/v1/auth/login/', {
      body: {
        ...input,
        refresh_token_transport: prepared.transport,
      },
      credentials: prepared.credentials,
      headers: buildTransportHeaders(prepared),
    })

    if (error || !data) {
      throw buildAuthError(response, error, 'Sign-in failed.')
    }

    await commitAuthEnvelope(data, prepared, {
      expectedGeneration: generation,
      purgeNonAuth: true,
    })

    return toBootstrapResponse(data)
  })
}

export async function validateRegistrationOwner(input: RegistrationOwnerValidateRequest) {
  const { error, response } = await apiClient.POST('/api/v1/auth/register/validate-owner/', {
    body: input,
    credentials: 'omit',
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

/** Registration payload; `establishment_name` may be omitted (backend generates a temp name). */
export type OnboardingRegistrationInput = Omit<RegistrationRequest, 'establishment_name'> & {
  establishment_name?: string
}

export async function registerOnboarding(input: OnboardingRegistrationInput) {
  return runSessionReplacement(async (prepared, generation) => {
    const { data, error, response } = await apiClient.POST('/api/v1/auth/register/', {
      body: {
        ...input,
        establishment_name: input.establishment_name ?? '',
        refresh_token_transport: prepared.transport,
      },
      credentials: prepared.credentials,
      headers: buildTransportHeaders(prepared),
    })

    if (error || !data) {
      throw buildRegistrationValidationError(
        response,
        error,
        'Registration could not be completed.',
      )
    }

    await commitAuthEnvelope(data, prepared, {
      expectedGeneration: generation,
      purgeNonAuth: true,
    })

    return {
      establishment_id: data.establishment_id,
      onboarding_session_id: data.onboarding_session_id,
    } satisfies Pick<RegistrationResponse, 'establishment_id' | 'onboarding_session_id'>
  })
}

export async function acceptInvitationSession(
  token: string,
  input: DirectorInvitationAcceptInput,
) {
  return runSessionReplacement(async (prepared, generation) => {
    const { data, error, response } = await apiClient.POST(
      '/api/v1/invitations/{token}/accept/',
      {
        params: {
          path: { token },
        },
        body: {
          ...input,
          refresh_token_transport: prepared.transport,
        },
        credentials: prepared.credentials,
        headers: buildTransportHeaders(prepared),
      },
    )

    if (error || !data) {
      throw buildAuthError(response, error, 'Invitation could not be accepted.')
    }

    await commitAuthEnvelope(data, prepared, {
      expectedGeneration: generation,
      purgeNonAuth: true,
    })
  })
}

export async function logout() {
  await runNativePushBeforeLogout()
  const accessToken = getAccessToken()
  const prepared = await prepareLogoutTransport()
  const { error, response } = await apiClient.POST('/api/v1/auth/logout/', {
    body: {
      refresh_token_transport: prepared.transport,
      ...(prepared.refreshToken ? { refresh_token: prepared.refreshToken } : {}),
    },
    credentials: prepared.credentials,
    headers: buildTransportHeaders(prepared, accessToken),
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
  clearAllPlanningSubmissionIntents()
  clearSuccessToasts()
  queryClient.setQueryData<BootstrapResponse>(bootstrapQueryKey, result.data)
  return result.data
}

export async function createEstablishment(
  input: EstablishmentCreateRequest,
): Promise<EstablishmentCreateResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/', {
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
    throw buildAuthError(
      result.response,
      result.error,
      'We could not create this establishment.',
    )
  }

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

  return result.data as EstablishmentMembershipDetailResponse
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

  return result.data as EstablishmentMembershipDetailResponse
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

export async function reinviteMembership(establishmentId: string, membershipId: string) {
  const csrfToken = await ensureCsrfToken()
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/memberships/{membership_id}/reinvite/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              membership_id: membershipId,
            },
          },
          credentials: 'include',
          headers: {
            Authorization: `Bearer ${accessToken}`,
            'X-CSRFToken': csrfToken,
          },
        },
      ),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildAuthError(result.response, result.error, 'Invitation could not be resent.')
  }

  return result.data as MembershipReinviteResponse
}

export const businessUnitTreeQueryKey = (establishmentId: string) =>
  ['workspace', 'business-units', establishmentId] as const

export type { BusinessUnitTreeResponse }

export async function fetchBusinessUnitTree(
  establishmentId: string,
  options?: { includeInactive?: boolean },
): Promise<BusinessUnitTreeResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/business-units/', {
        params: {
          path: { establishment_id: establishmentId },
          ...(options?.includeInactive ? { query: { include_inactive: true } } : {}),
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
    throw new AuthApiError('Business unit tree could not be loaded.', result.response.status)
  }

  return result.data
}

export { AuthApiError }
