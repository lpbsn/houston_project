import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createEstablishment } from '@/features/auth/api'

import {
  getOrganizationMemberFilterOptions,
  getOrganizationOverview,
  invalidateOrganizationQueries,
  inviteOrganizationOwner,
  listOrganizationEstablishments,
  listOrganizationMembers,
  listOrganizationOwners,
  organizationEstablishmentsQueryKey,
  organizationMemberFilterOptionsQueryKey,
  organizationMembersQueryKey,
  organizationOverviewQueryKey,
  organizationOwnersQueryKey,
} from './api'
import type {
  OrganizationAdminOwnerInvitationRequest,
  OrganizationMemberListFilters,
} from './types'

export function useOrganizationOverviewQuery(organizationId: string | null) {
  return useQuery({
    queryKey: organizationId
      ? organizationOverviewQueryKey(organizationId)
      : ['organization', 'overview', 'disabled'],
    queryFn: () => getOrganizationOverview(organizationId!),
    enabled: Boolean(organizationId),
  })
}

export function useOrganizationEstablishmentsQuery(organizationId: string | null) {
  return useQuery({
    queryKey: organizationId
      ? organizationEstablishmentsQueryKey(organizationId)
      : ['organization', 'establishments', 'disabled'],
    queryFn: () => listOrganizationEstablishments(organizationId!),
    enabled: Boolean(organizationId),
  })
}

export function useOrganizationMembersQuery(
  organizationId: string | null,
  filters: OrganizationMemberListFilters,
) {
  return useQuery({
    queryKey: organizationId
      ? organizationMembersQueryKey(organizationId, filters)
      : ['organization', 'members', 'disabled'],
    queryFn: () => listOrganizationMembers(organizationId!, filters),
    enabled: Boolean(organizationId),
  })
}

export function useOrganizationMemberFilterOptionsQuery(organizationId: string | null) {
  return useQuery({
    queryKey: organizationId
      ? organizationMemberFilterOptionsQueryKey(organizationId)
      : ['organization', 'member-filter-options', 'disabled'],
    queryFn: () => getOrganizationMemberFilterOptions(organizationId!),
    enabled: Boolean(organizationId),
  })
}

export function useOrganizationOwnersQuery(organizationId: string | null) {
  return useQuery({
    queryKey: organizationId
      ? organizationOwnersQueryKey(organizationId)
      : ['organization', 'owners', 'disabled'],
    queryFn: () => listOrganizationOwners(organizationId!),
    enabled: Boolean(organizationId),
  })
}

export function useInviteOrganizationOwnerMutation(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: OrganizationAdminOwnerInvitationRequest) =>
      inviteOrganizationOwner(organizationId, body),
    onSuccess: async () => {
      await invalidateOrganizationQueries(organizationId)
      await queryClient.invalidateQueries({
        queryKey: organizationOwnersQueryKey(organizationId),
      })
    },
  })
}

export function useCreateOrganizationEstablishmentMutation(organizationId: string) {
  return useMutation({
    mutationFn: (name: string) => createEstablishment({ name }),
    onSuccess: async () => {
      await invalidateOrganizationQueries(organizationId)
    },
  })
}
