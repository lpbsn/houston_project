import { apiClient, withAuthRetry } from '@/api/client'
import { bootstrapQueryKey } from '@/features/auth/api'
import { queryClient } from '@/lib/query-client'

import type {
  DirectorInvitationResponse,
  OrganizationAdminEstablishmentList,
  OrganizationAdminMemberFilterOptions,
  OrganizationAdminMemberList,
  OrganizationAdminOverview,
  OrganizationAdminOwnerInvitationRequest,
  OrganizationAdminOwnerList,
  OrganizationMemberListFilters,
} from './types'

export const organizationQueryKeyRoot = ['organization'] as const

export const organizationOverviewQueryKey = (organizationId: string) =>
  [...organizationQueryKeyRoot, organizationId, 'overview'] as const

export const organizationEstablishmentsQueryKey = (organizationId: string) =>
  [...organizationQueryKeyRoot, organizationId, 'establishments'] as const

export const organizationMembersQueryKey = (
  organizationId: string,
  filters: OrganizationMemberListFilters = {},
) => [...organizationQueryKeyRoot, organizationId, 'members', filters] as const

export const organizationMemberFilterOptionsQueryKey = (organizationId: string) =>
  [...organizationQueryKeyRoot, organizationId, 'member-filter-options'] as const

export const organizationOwnersQueryKey = (organizationId: string) =>
  [...organizationQueryKeyRoot, organizationId, 'owners'] as const

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

export async function getOrganizationOverview(
  organizationId: string,
): Promise<OrganizationAdminOverview> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/organizations/{organization_id}/', {
        params: { path: { organization_id: organizationId } },
        headers: authHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOrganizationError(
      result.response,
      result.error,
      'Impossible de charger l’organisation.',
    )
  }

  return result.data
}

export async function listOrganizationEstablishments(
  organizationId: string,
): Promise<OrganizationAdminEstablishmentList> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/organizations/{organization_id}/establishments/', {
        params: { path: { organization_id: organizationId } },
        headers: authHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOrganizationError(
      result.response,
      result.error,
      'Impossible de charger les établissements.',
    )
  }

  return result.data
}

export async function listOrganizationMembers(
  organizationId: string,
  filters: OrganizationMemberListFilters = {},
): Promise<OrganizationAdminMemberList> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/organizations/{organization_id}/members/', {
        params: {
          path: { organization_id: organizationId },
          query: {
            q: filters.q || undefined,
            establishment_id: filters.establishment_id || undefined,
            business_unit_id: filters.business_unit_id || undefined,
            role: filters.role || undefined,
            status: filters.status || undefined,
          },
        },
        headers: authHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOrganizationError(
      result.response,
      result.error,
      'Impossible de charger les membres.',
    )
  }

  return result.data
}

export async function getOrganizationMemberFilterOptions(
  organizationId: string,
): Promise<OrganizationAdminMemberFilterOptions> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/organizations/{organization_id}/members/filter-options/', {
        params: { path: { organization_id: organizationId } },
        headers: authHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOrganizationError(
      result.response,
      result.error,
      'Impossible de charger les filtres membres.',
    )
  }

  return result.data
}

export async function listOrganizationOwners(
  organizationId: string,
): Promise<OrganizationAdminOwnerList> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/organizations/{organization_id}/owners/', {
        params: { path: { organization_id: organizationId } },
        headers: authHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOrganizationError(
      result.response,
      result.error,
      'Impossible de charger les propriétaires.',
    )
  }

  return result.data
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

export async function invalidateOrganizationQueries(organizationId: string) {
  await Promise.allSettled([
    queryClient.invalidateQueries({ queryKey: organizationQueryKeyRoot }),
    queryClient.invalidateQueries({
      queryKey: organizationOverviewQueryKey(organizationId),
    }),
    queryClient.invalidateQueries({
      queryKey: organizationEstablishmentsQueryKey(organizationId),
    }),
    queryClient.invalidateQueries({
      queryKey: [...organizationQueryKeyRoot, organizationId, 'members'],
    }),
    queryClient.invalidateQueries({
      queryKey: organizationOwnersQueryKey(organizationId),
    }),
    queryClient.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true }),
  ])
}
