import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createEstablishment } from '@/features/auth/api'

import {
  activateEstablishmentAdminMembership,
  deactivateEstablishmentAdminMembership,
  establishmentAdminMemberFilterOptionsQueryKey,
  establishmentAdminMembershipsQueryKey,
  establishmentAdminOverviewQueryKey,
  getEstablishmentAdminMemberFilterOptions,
  getEstablishmentAdminOverview,
  getOrganizationMemberFilterOptions,
  getOrganizationOverview,
  invalidateEstablishmentAdminQueries,
  invalidateOrganizationQueries,
  inviteEstablishmentAdminMembership,
  inviteOrganizationOwner,
  listEstablishmentAdminMemberships,
  listOrganizationEstablishments,
  listOrganizationMembers,
  listOrganizationOwners,
  organizationEstablishmentsQueryKey,
  organizationMemberFilterOptionsQueryKey,
  organizationMembersQueryKey,
  organizationOverviewQueryKey,
  organizationOwnersQueryKey,
  updateEstablishmentAdminMembership,
} from './api'
import type {
  EstablishmentAdminMemberListFilters,
  EstablishmentAdminMembershipInvitationRequest,
  OrganizationAdminOwnerInvitationRequest,
  OrganizationMemberListFilters,
  PatchedEstablishmentAdminMembershipUpdateRequest,
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

export function useEstablishmentAdminOverviewQuery(establishmentId: string | null) {
  return useQuery({
    queryKey: establishmentId
      ? establishmentAdminOverviewQueryKey(establishmentId)
      : ['organization', 'establishment', 'overview', 'disabled'],
    queryFn: () => getEstablishmentAdminOverview(establishmentId!),
    enabled: Boolean(establishmentId),
  })
}

export function useEstablishmentAdminMembershipsQuery(
  establishmentId: string | null,
  filters: EstablishmentAdminMemberListFilters,
) {
  return useQuery({
    queryKey: establishmentId
      ? establishmentAdminMembershipsQueryKey(establishmentId, filters)
      : ['organization', 'establishment', 'memberships', 'disabled'],
    queryFn: () => listEstablishmentAdminMemberships(establishmentId!, filters),
    enabled: Boolean(establishmentId),
  })
}

export function useEstablishmentAdminMemberFilterOptionsQuery(
  establishmentId: string | null,
) {
  return useQuery({
    queryKey: establishmentId
      ? establishmentAdminMemberFilterOptionsQueryKey(establishmentId)
      : ['organization', 'establishment', 'membership-filter-options', 'disabled'],
    queryFn: () => getEstablishmentAdminMemberFilterOptions(establishmentId!),
    enabled: Boolean(establishmentId),
  })
}

export function useInviteEstablishmentAdminMembershipMutation(establishmentId: string) {
  return useMutation({
    mutationFn: (body: EstablishmentAdminMembershipInvitationRequest) =>
      inviteEstablishmentAdminMembership(establishmentId, body),
    onSuccess: async () => {
      await invalidateEstablishmentAdminQueries(establishmentId)
    },
  })
}

export function useUpdateEstablishmentAdminMembershipMutation(establishmentId: string) {
  return useMutation({
    mutationFn: (input: {
      membershipId: string
      body: PatchedEstablishmentAdminMembershipUpdateRequest
    }) => updateEstablishmentAdminMembership(establishmentId, input.membershipId, input.body),
    onSuccess: async () => {
      await invalidateEstablishmentAdminQueries(establishmentId)
    },
  })
}

export function useDeactivateEstablishmentAdminMembershipMutation(establishmentId: string) {
  return useMutation({
    mutationFn: (membershipId: string) =>
      deactivateEstablishmentAdminMembership(establishmentId, membershipId),
    onSuccess: async () => {
      await invalidateEstablishmentAdminQueries(establishmentId)
    },
  })
}

export function useActivateEstablishmentAdminMembershipMutation(establishmentId: string) {
  return useMutation({
    mutationFn: (membershipId: string) =>
      activateEstablishmentAdminMembership(establishmentId, membershipId),
    onSuccess: async () => {
      await invalidateEstablishmentAdminQueries(establishmentId)
    },
  })
}
