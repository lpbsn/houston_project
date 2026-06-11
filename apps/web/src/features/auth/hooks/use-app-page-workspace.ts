import { startTransition, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'
import { toErrorMessage } from '@/lib/error-message'
import {
  deactivateMembership,
  getMembership,
  getWorkspaceSummary,
  listMemberships,
  membershipDetailQueryKey,
  membershipListQueryKey,
  switchEstablishment,
  updateMembership,
  workspaceSummaryQueryKey,
} from '@/features/auth/api'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import {
  businessUnitScopesFromApiItems,
  type BusinessUnitScopeSelection,
} from '@/features/auth/lib/business-unit-scope'
import { canEditMembershipOperationalScopes } from '@/features/auth/lib/membership-rbac'
import type {
  EstablishmentMembershipResponse,
  MembershipUpdateRequest,
  RoleEnum,
} from '@/features/auth/types'

const ROLE_OPTIONS: RoleEnum[] = ['owner', 'director', 'manager', 'staff']
const EMPTY_MEMBERSHIPS: EstablishmentMembershipResponse[] = []

function normalizeRole(role: string | null | undefined): RoleEnum {
  return ROLE_OPTIONS.find((candidate) => candidate === role) ?? 'staff'
}

type UseAppPageWorkspaceOptions = {
  membershipManagementEnabled: boolean
}

export function useAppPageWorkspace({ membershipManagementEnabled }: UseAppPageWorkspaceOptions) {
  const queryClient = useQueryClient()
  const { activeMembership, memberships } = useAuth()
  const [pendingEstablishmentId, setPendingEstablishmentId] = useState<string | null>(null)
  const [selectorError, setSelectorError] = useState<string | null>(null)
  const [selectedMembershipId, setSelectedMembershipId] = useState<string | null>(null)
  const [editorState, setEditorState] = useState<{
    membershipId: string | null
    roleDraft: RoleEnum
    selectedScopes: BusinessUnitScopeSelection[]
  }>({
    membershipId: null,
    roleDraft: 'staff',
    selectedScopes: [],
  })
  const [membershipMutationError, setMembershipMutationError] = useState<string | null>(null)

  const activeEstablishmentId = activeMembership?.establishment_id ?? null
  const actorRole = normalizeRole(activeMembership?.role)
  const needsEstablishmentSelection = memberships.length > 1 && !activeMembership

  const switchMutation = useMutation({
    mutationFn: switchEstablishment,
  })

  const workspaceSummaryQuery = useQuery({
    queryKey: activeEstablishmentId
      ? workspaceSummaryQueryKey(activeEstablishmentId)
      : ['workspace', 'summary', 'idle'],
    queryFn: () => getWorkspaceSummary(activeEstablishmentId!),
    enabled: Boolean(activeEstablishmentId),
    staleTime: 30_000,
  })

  const membershipsQuery = useQuery({
    queryKey: activeEstablishmentId
      ? membershipListQueryKey(activeEstablishmentId)
      : ['workspace', 'memberships', 'idle'],
    queryFn: () => listMemberships(activeEstablishmentId!),
    enabled: Boolean(activeEstablishmentId && membershipManagementEnabled),
    staleTime: 30_000,
  })

  const businessUnitQuery = useBusinessUnitTreeQuery(activeEstablishmentId, {
    enabled: Boolean(activeEstablishmentId && membershipManagementEnabled),
    staleTime: 60_000,
  })

  const membershipList = membershipsQuery.data ?? EMPTY_MEMBERSHIPS
  const effectiveSelectedMembershipId = useMemo(() => {
    if (membershipList.length === 0) {
      return null
    }

    if (
      selectedMembershipId &&
      membershipList.some((membership) => membership.id === selectedMembershipId)
    ) {
      return selectedMembershipId
    }

    return membershipList[0].id
  }, [membershipList, selectedMembershipId])

  const membershipDetailQuery = useQuery({
    queryKey:
      activeEstablishmentId && effectiveSelectedMembershipId
        ? membershipDetailQueryKey(activeEstablishmentId, effectiveSelectedMembershipId)
        : ['workspace', 'membership-detail', 'idle'],
    queryFn: () => getMembership(activeEstablishmentId!, effectiveSelectedMembershipId!),
    enabled: Boolean(
      activeEstablishmentId && effectiveSelectedMembershipId && membershipManagementEnabled,
    ),
    staleTime: 30_000,
  })

  const updateMutation = useMutation({
    mutationFn: async (input: MembershipUpdateRequest) => {
      if (!activeEstablishmentId || !effectiveSelectedMembershipId) {
        throw new Error('Select a membership before saving changes.')
      }

      return updateMembership(activeEstablishmentId, effectiveSelectedMembershipId, input)
    },
    onSuccess: async (membership) => {
      if (!activeEstablishmentId) {
        return
      }

      queryClient.setQueryData(
        membershipDetailQueryKey(activeEstablishmentId, membership.id),
        membership,
      )
      await queryClient.invalidateQueries({ queryKey: membershipListQueryKey(activeEstablishmentId) })
      await queryClient.invalidateQueries({
        queryKey: workspaceSummaryQueryKey(activeEstablishmentId),
      })
      setEditorState({
        membershipId: membership.id,
        roleDraft: normalizeRole(membership.role),
        selectedScopes: businessUnitScopesFromApiItems(membership.scopes),
      })
      setMembershipMutationError(null)
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: async () => {
      if (!activeEstablishmentId || !effectiveSelectedMembershipId) {
        throw new Error('Select a membership before deactivating it.')
      }

      return deactivateMembership(activeEstablishmentId, effectiveSelectedMembershipId)
    },
    onSuccess: async () => {
      if (!activeEstablishmentId) {
        return
      }

      await queryClient.invalidateQueries({ queryKey: membershipListQueryKey(activeEstablishmentId) })
      await queryClient.invalidateQueries({
        queryKey: workspaceSummaryQueryKey(activeEstablishmentId),
      })
      startTransition(() => {
        setSelectedMembershipId(null)
        setEditorState({
          membershipId: null,
          roleDraft: 'staff',
          selectedScopes: [],
        })
        setMembershipMutationError(null)
      })
    },
  })

  const selectedMembership = membershipDetailQuery.data ?? null
  const roleDraft =
    editorState.membershipId === selectedMembership?.id
      ? editorState.roleDraft
      : normalizeRole(selectedMembership?.role)
  const selectedScopes = useMemo(() => {
    if (editorState.membershipId === selectedMembership?.id) {
      return editorState.selectedScopes
    }

    return selectedMembership ? businessUnitScopesFromApiItems(selectedMembership.scopes) : []
  }, [editorState.membershipId, editorState.selectedScopes, selectedMembership])

  async function handleSelectEstablishment(establishmentId: string) {
    setSelectorError(null)
    setPendingEstablishmentId(establishmentId)

    try {
      await switchMutation.mutateAsync({ establishment_id: establishmentId })
      startTransition(() => {
        setSelectedMembershipId(null)
        setEditorState({
          membershipId: null,
          roleDraft: 'staff',
          selectedScopes: [],
        })
        setMembershipMutationError(null)
      })
    } catch (error) {
      setSelectorError(toErrorMessage(error, 'We could not switch this establishment.'))
    } finally {
      setPendingEstablishmentId(null)
    }
  }

  async function handleSaveMembership() {
    if (canEditMembershipOperationalScopes(roleDraft) && selectedScopes.length === 0) {
      setMembershipMutationError('Sélectionnez au moins un pôle d’activité.')
      return
    }

    const nextInput: MembershipUpdateRequest = {
      role: roleDraft,
    }

    if (canEditMembershipOperationalScopes(roleDraft)) {
      nextInput.scopes = selectedScopes
    }

    try {
      await updateMutation.mutateAsync(nextInput)
    } catch (error) {
      setMembershipMutationError(toErrorMessage(error, 'Membership changes were not saved.'))
    }
  }

  async function handleDeactivateMembership() {
    try {
      await deactivateMutation.mutateAsync()
    } catch (error) {
      setMembershipMutationError(
        toErrorMessage(error, 'This membership could not be deactivated.'),
      )
    }
  }

  function handleRoleChange(role: RoleEnum) {
    setEditorState({
      membershipId: selectedMembership?.id ?? effectiveSelectedMembershipId,
      roleDraft: role,
      selectedScopes,
    })
  }

  function handleScopesChange(scopes: BusinessUnitScopeSelection[]) {
    setEditorState({
      membershipId: selectedMembership?.id ?? effectiveSelectedMembershipId,
      roleDraft,
      selectedScopes: scopes,
    })
  }

  function handleSelectMembership(membershipId: string) {
    setSelectedMembershipId(membershipId)
    setEditorState({
      membershipId: null,
      roleDraft: 'staff',
      selectedScopes: [],
    })
    setMembershipMutationError(null)
  }

  const scopeBusinessUnitError = businessUnitQuery.error
    ? toErrorMessage(businessUnitQuery.error, 'Les pôles d’activité sont indisponibles.')
    : null

  return {
    activeMembership,
    actorRole,
    businessUnitQuery,
    deactivateMutation,
    effectiveSelectedMembershipId,
    handleDeactivateMembership,
    handleRoleChange,
    handleSaveMembership,
    handleScopesChange,
    handleSelectEstablishment,
    handleSelectMembership,
    membershipDetailQuery,
    membershipList,
    membershipMutationError,
    memberships,
    membershipsQuery,
    needsEstablishmentSelection,
    pendingEstablishmentId,
    roleDraft,
    scopeBusinessUnitError,
    selectedMembership,
    selectedScopes,
    selectorError,
    updateMutation,
    workspaceSummaryQuery,
  }
}
