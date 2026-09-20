import { apiClient, withAuthRetry } from '@/api/client'

import { OnboardingApiError } from '@/features/onboarding/api'
import type { OnboardingDraftPayload } from '@/features/onboarding/lib/onboarding-draft-payload'
import type { OnboardingDraftResponse } from '@/features/onboarding/types'

function getAuthHeaders(accessToken: string | null) {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function throwApiError(response: Response, error: unknown, fallback: string): never {
  const detail =
    isRecord(error) && typeof error.detail === 'string' ? error.detail : fallback
  const code = isRecord(error) && typeof error.code === 'string' ? error.code : null
  throw new OnboardingApiError({
    status: response.status,
    detail,
    code,
    payload: error,
  })
}

export type PlatformMembershipFilters = {
  user_id?: string
  establishment_id?: string
  organization_id?: string
}

export const platformQueryKeys = {
  all: ['platform'] as const,
  organizations: (q: string) => ['platform', 'organizations', q] as const,
  organization: (id: string) => ['platform', 'organizations', 'detail', id] as const,
  establishments: (q: string, organizationId = '') =>
    ['platform', 'establishments', q, organizationId] as const,
  establishment: (id: string) => ['platform', 'establishments', 'detail', id] as const,
  users: (q: string) => ['platform', 'users', q] as const,
  user: (id: string) => ['platform', 'users', 'detail', id] as const,
  onboardings: (q: string) => ['platform', 'onboardings', q] as const,
  onboarding: (id: string) => ['platform', 'onboardings', 'detail', id] as const,
  draft: (id: string) => ['platform', 'onboardings', id, 'draft'] as const,
  memberships: (filters: PlatformMembershipFilters) =>
    [
      'platform',
      'memberships',
      filters.organization_id ?? '',
      filters.establishment_id ?? '',
      filters.user_id ?? '',
    ] as const,
}

export async function listPlatformOnboardings(q = '', cursor?: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/platform/onboardings/', {
        params: {
          query: {
            q: q || undefined,
            cursor: cursor || undefined,
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Impossible de charger les onboardings.')
  }
  return result.data
}

export async function startPlatformOnboarding(body: {
  organization_name: string
  establishment_name?: string | null
}) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/platform/onboardings/', {
        body,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Impossible de démarrer l’onboarding.')
  }
  return result.data
}

export async function getPlatformOnboarding(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/platform/onboardings/{session_id}/', {
        params: { path: { session_id: sessionId } },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Onboarding introuvable.')
  }
  return result.data
}

export async function getPlatformOnboardingDraft(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/platform/onboardings/{session_id}/draft/', {
        params: { path: { session_id: sessionId } },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Impossible de charger le brouillon.')
  }
  return result.data as OnboardingDraftResponse
}

export async function putPlatformOnboardingDraft(
  sessionId: string,
  payload: OnboardingDraftPayload,
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PUT('/api/v1/platform/onboardings/{session_id}/draft/', {
        params: { path: { session_id: sessionId } },
        body: { payload },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Impossible d’enregistrer le brouillon.')
  }
  return result.data as OnboardingDraftResponse
}

export async function completePlatformOnboarding(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/platform/onboardings/{session_id}/complete/', {
        params: { path: { session_id: sessionId } },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Impossible de finaliser l’onboarding.')
  }
  return result.data
}

export async function invitePlatformOwner(
  sessionId: string,
  body: { email: string; first_name: string; last_name: string },
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/platform/onboardings/{session_id}/owner-invitations/', {
        params: { path: { session_id: sessionId } },
        body,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Impossible d’inviter l’Owner.')
  }
  return result.data
}

export async function listPlatformOrganizations(q = '', cursor?: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/platform/organizations/', {
        params: { query: { q: q || undefined, cursor: cursor || undefined } },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Impossible de charger les organisations.')
  }
  return result.data
}

export async function getPlatformOrganization(organizationId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/platform/organizations/{organization_id}/', {
        params: { path: { organization_id: organizationId } },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Organisation introuvable.')
  }
  return result.data
}

export async function deletePlatformOrganization(organizationId: string, justification: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/platform/organizations/{organization_id}/delete/', {
        params: { path: { organization_id: organizationId } },
        body: { justification },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || result.response.status !== 204) {
    throwApiError(result.response, result.error, 'Suppression refusée.')
  }
}

export async function listPlatformEstablishments(
  q = '',
  options: { cursor?: string; organization_id?: string } = {},
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/platform/establishments/', {
        params: {
          query: {
            q: q || undefined,
            cursor: options.cursor || undefined,
            organization_id: options.organization_id || undefined,
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Impossible de charger les établissements.')
  }
  return result.data
}

export async function getPlatformEstablishment(establishmentId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/platform/establishments/{establishment_id}/', {
        params: { path: { establishment_id: establishmentId } },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Établissement introuvable.')
  }
  return result.data
}

export async function deletePlatformEstablishment(establishmentId: string, justification: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/platform/establishments/{establishment_id}/delete/', {
        params: { path: { establishment_id: establishmentId } },
        body: { justification },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || result.response.status !== 204) {
    throwApiError(result.response, result.error, 'Suppression refusée.')
  }
}

export async function listPlatformUsers(q = '', cursor?: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/platform/users/', {
        params: { query: { q: q || undefined, cursor: cursor || undefined } },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Impossible de charger les utilisateurs.')
  }
  return result.data
}

export async function getPlatformUser(userId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/platform/users/{user_id}/', {
        params: { path: { user_id: userId } },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Utilisateur introuvable.')
  }
  return result.data
}

export async function listPlatformMemberships(
  filters: PlatformMembershipFilters,
  cursor?: string,
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/platform/memberships/', {
        params: {
          query: {
            user_id: filters.user_id || undefined,
            establishment_id: filters.establishment_id || undefined,
            organization_id: filters.organization_id || undefined,
            cursor: cursor || undefined,
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    throwApiError(result.response, result.error, 'Impossible de charger les rattachements.')
  }
  return result.data
}
