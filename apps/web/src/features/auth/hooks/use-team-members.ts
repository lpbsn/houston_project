import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'
import {
  activateMembership,
  deactivateMembership,
  getMembership,
  invalidateMembershipListAndDetailQueries,
  invalidateMembershipWorkspaceQueries,
  listMemberships,
  membershipDetailQueryKey,
  membershipListQueryKey,
  patchMembershipCaches,
  updateMembership,
  updateUserProfile,
  type UserProfileUpdateRequest,
} from '@/features/auth/api'
import {
  canViewTeamFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import type { EstablishmentMembershipResponse, MembershipUpdateRequest } from '@/features/auth/types'

export function useTeamMembersQuery() {
  const { activeMembership, bootstrap } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null
  const canViewTeam = canViewTeamFromBootstrapHints(getBootstrapPermissionHints(bootstrap))

  return useQuery({
    queryKey: establishmentId ? membershipListQueryKey(establishmentId) : ['workspace', 'memberships', 'idle'],
    queryFn: () => listMemberships(establishmentId!),
    enabled: Boolean(establishmentId && canViewTeam),
    staleTime: 30_000,
  })
}

export function useTeamMemberDetailQuery(membershipId: string | null) {
  const { activeMembership, bootstrap } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null
  const canViewTeam = canViewTeamFromBootstrapHints(getBootstrapPermissionHints(bootstrap))

  return useQuery({
    queryKey:
      establishmentId && membershipId
        ? membershipDetailQueryKey(establishmentId, membershipId)
        : ['workspace', 'memberships', 'detail', 'idle'],
    queryFn: () => getMembership(establishmentId!, membershipId!),
    enabled: Boolean(establishmentId && membershipId && canViewTeam),
    staleTime: 30_000,
  })
}

function useTeamMembershipMutationContext() {
  const queryClient = useQueryClient()
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  const applyMembershipWriteSuccess = (membership: EstablishmentMembershipResponse) => {
    if (establishmentId) {
      patchMembershipCaches(establishmentId, membership, queryClient)
    }

    if (membership.role === 'owner') {
      void invalidateMembershipWorkspaceQueries({
        includeBootstrap: true,
        queryClient,
      })
      return
    }

    if (!establishmentId) {
      return
    }

    void invalidateMembershipListAndDetailQueries(establishmentId, membership.id, queryClient)
  }

  return { establishmentId, applyMembershipWriteSuccess }
}

export function useUpdateMembershipMutation(membershipId: string) {
  const { establishmentId, applyMembershipWriteSuccess } = useTeamMembershipMutationContext()

  return useMutation({
    mutationFn: (input: MembershipUpdateRequest) =>
      updateMembership(establishmentId!, membershipId, input),
    onSuccess: (data) => {
      applyMembershipWriteSuccess(data)
    },
  })
}

export function useActivateMembershipMutation(membershipId: string) {
  const { establishmentId, applyMembershipWriteSuccess } = useTeamMembershipMutationContext()

  return useMutation({
    mutationFn: () => activateMembership(establishmentId!, membershipId),
    onSuccess: (data) => {
      applyMembershipWriteSuccess(data)
    },
  })
}

export function useDeactivateMembershipMutation(membershipId: string) {
  const { establishmentId, applyMembershipWriteSuccess } = useTeamMembershipMutationContext()

  return useMutation({
    mutationFn: () => deactivateMembership(establishmentId!, membershipId),
    onSuccess: (data) => {
      applyMembershipWriteSuccess(data)
    },
  })
}

export function useUpdateProfileMutation() {
  const queryClient = useQueryClient()
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  return useMutation({
    mutationFn: (input: UserProfileUpdateRequest) => updateUserProfile(input),
    onSuccess: () => {
      if (establishmentId && activeMembership?.id) {
        void invalidateMembershipListAndDetailQueries(
          establishmentId,
          activeMembership.id,
          queryClient,
        )
      }
    },
  })
}
