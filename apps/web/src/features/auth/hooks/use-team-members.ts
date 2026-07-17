import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'
import {
  activateMembership,
  deactivateMembership,
  getMembership,
  invalidateMembershipWorkspaceQueries,
  listMemberships,
  membershipDetailQueryKey,
  membershipListQueryKey,
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

  const invalidateMembershipQueries = async (
    membershipId: string,
    membership?: EstablishmentMembershipResponse | null,
  ) => {
    if (membership?.role === 'owner') {
      await invalidateMembershipWorkspaceQueries({ includeBootstrap: true })
      return
    }

    if (!establishmentId) {
      return
    }
    await queryClient.invalidateQueries({
      queryKey: membershipListQueryKey(establishmentId),
    })
    await queryClient.invalidateQueries({
      queryKey: membershipDetailQueryKey(establishmentId, membershipId),
    })
  }

  return { establishmentId, invalidateMembershipQueries }
}

export function useUpdateMembershipMutation(membershipId: string) {
  const { establishmentId, invalidateMembershipQueries } = useTeamMembershipMutationContext()

  return useMutation({
    mutationFn: (input: MembershipUpdateRequest) =>
      updateMembership(establishmentId!, membershipId, input),
    onSuccess: async (data) => {
      await invalidateMembershipQueries(membershipId, data)
    },
  })
}

export function useActivateMembershipMutation(membershipId: string) {
  const { establishmentId, invalidateMembershipQueries } = useTeamMembershipMutationContext()

  return useMutation({
    mutationFn: () => activateMembership(establishmentId!, membershipId),
    onSuccess: async (data) => {
      await invalidateMembershipQueries(membershipId, data)
    },
  })
}

export function useDeactivateMembershipMutation(membershipId: string) {
  const { establishmentId, invalidateMembershipQueries } = useTeamMembershipMutationContext()

  return useMutation({
    mutationFn: () => deactivateMembership(establishmentId!, membershipId),
    onSuccess: async (data) => {
      await invalidateMembershipQueries(membershipId, data)
    },
  })
}

export function useUpdateProfileMutation() {
  const queryClient = useQueryClient()
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  return useMutation({
    mutationFn: (input: UserProfileUpdateRequest) => updateUserProfile(input),
    onSuccess: async () => {
      if (establishmentId && activeMembership?.id) {
        await queryClient.invalidateQueries({
          queryKey: membershipListQueryKey(establishmentId),
        })
        await queryClient.invalidateQueries({
          queryKey: membershipDetailQueryKey(establishmentId, activeMembership.id),
        })
      }
    },
  })
}
