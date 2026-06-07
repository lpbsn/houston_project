import { startTransition, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ClipboardCheck } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  deactivateMembership,
  getMembership,
  getOperationalTaxonomy,
  getWorkspaceSummary,
  listMemberships,
  membershipDetailQueryKey,
  membershipListQueryKey,
  operationalTaxonomyQueryKey,
  switchEstablishment,
  updateMembership,
  workspaceSummaryQueryKey,
} from '@/features/auth/api'
import { EstablishmentSelectorCard } from '@/features/auth/components/establishment-selector-card'
import { EstablishmentSummaryCard } from '@/features/auth/components/establishment-summary-card'
import { MembershipInviteCard } from '@/features/auth/components/membership-invite-card'
import { MembershipManagementCard } from '@/features/auth/components/membership-management-card'
import {
  buildOperationalScopeTree,
  normalizeScopesForSubmit,
  scopesFromApiItems,
  type MembershipScopeSelection,
} from '@/features/auth/lib/membership-scope'
import { canEditMembershipOperationalScopes } from '@/features/auth/lib/membership-rbac'
import type {
  EstablishmentMembershipResponse,
  MembershipUpdateRequest,
  RoleEnum,
} from '@/features/auth/types'

const MANAGEABLE_ROLES = new Set<RoleEnum>(['owner', 'director'])
const ROLE_OPTIONS: RoleEnum[] = ['owner', 'director', 'manager', 'staff']
const EMPTY_MEMBERSHIPS: EstablishmentMembershipResponse[] = []

function normalizeRole(role: string | null | undefined): RoleEnum {
  return ROLE_OPTIONS.find((candidate) => candidate === role) ?? 'staff'
}

function toErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallback
}

export function AppPage({ onNavigate }: { onNavigate?: (path: string) => void }) {
  const queryClient = useQueryClient()
  const { activeMembership, memberships } = useAuth()
  const [pendingEstablishmentId, setPendingEstablishmentId] = useState<string | null>(null)
  const [selectorError, setSelectorError] = useState<string | null>(null)
  const [selectedMembershipId, setSelectedMembershipId] = useState<string | null>(null)
  const [editorState, setEditorState] = useState<{
    membershipId: string | null
    roleDraft: RoleEnum
    selectedScopes: MembershipScopeSelection[]
  }>({
    membershipId: null,
    roleDraft: 'staff',
    selectedScopes: [],
  })
  const [membershipMutationError, setMembershipMutationError] = useState<string | null>(null)

  const activeEstablishmentId = activeMembership?.establishment_id ?? null
  const actorRole = normalizeRole(activeMembership?.role)
  const canManageMemberships = MANAGEABLE_ROLES.has(actorRole)
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
    enabled: Boolean(activeEstablishmentId && canManageMemberships),
    staleTime: 30_000,
  })

  const taxonomyQuery = useQuery({
    queryKey: activeEstablishmentId
      ? operationalTaxonomyQueryKey(activeEstablishmentId)
      : ['workspace', 'operational-taxonomy', 'idle'],
    queryFn: () => getOperationalTaxonomy(activeEstablishmentId!),
    enabled: Boolean(activeEstablishmentId && canManageMemberships),
    staleTime: 60_000,
  })

  const scopeTree = useMemo(
    () => (taxonomyQuery.data ? buildOperationalScopeTree(taxonomyQuery.data) : null),
    [taxonomyQuery.data],
  )

  const membershipList = membershipsQuery.data ?? EMPTY_MEMBERSHIPS
  const effectiveSelectedMembershipId = useMemo(() => {
    if (membershipList.length === 0) {
      return null
    }

    if (selectedMembershipId && membershipList.some((membership) => membership.id === selectedMembershipId)) {
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
    enabled: Boolean(activeEstablishmentId && effectiveSelectedMembershipId && canManageMemberships),
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
        selectedScopes: scopesFromApiItems(membership.scopes),
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

    return selectedMembership ? scopesFromApiItems(selectedMembership.scopes) : []
  }, [editorState.membershipId, editorState.selectedScopes, selectedMembership])

  const normalizedScopes = useMemo(
    () => (scopeTree ? normalizeScopesForSubmit(selectedScopes, scopeTree) : []),
    [scopeTree, selectedScopes],
  )

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
    if (canEditMembershipOperationalScopes(roleDraft) && normalizedScopes.length === 0) {
      setMembershipMutationError('Sélectionnez au moins une zone de responsabilité.')
      return
    }

    const nextInput: MembershipUpdateRequest = {
      role: roleDraft,
    }

    if (canEditMembershipOperationalScopes(roleDraft)) {
      nextInput.scopes = normalizedScopes
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

  function handleScopesChange(scopes: MembershipScopeSelection[]) {
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

  const scopeTaxonomyError = taxonomyQuery.error
    ? toErrorMessage(taxonomyQuery.error, 'La taxonomie opérationnelle est indisponible.')
    : null

  return (
    <div className="space-y-4 sm:space-y-5">
      <EstablishmentSummaryCard
        isLoading={workspaceSummaryQuery.isPending}
        summary={workspaceSummaryQuery.data ?? null}
        errorMessage={
          workspaceSummaryQuery.error
            ? toErrorMessage(workspaceSummaryQuery.error, 'Establishment summary is unavailable.')
            : null
        }
      />

      {needsEstablishmentSelection ? (
        <EstablishmentSelectorCard
          memberships={memberships}
          pendingEstablishmentId={pendingEstablishmentId}
          onSelect={handleSelectEstablishment}
          errorMessage={selectorError}
        />
      ) : null}

      {activeMembership ? (
        <Card className="rounded-[1.75rem] border-[#e7dfd1] bg-[#fffaf2]">
          <CardHeader className="gap-2">
            <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
              Terrain
            </Badge>
            <CardTitle className="text-xl font-semibold">Faire remonter une observation</CardTitle>
            <CardDescription className="text-sm">
              Texte ou dictée audio, photos optionnelles (max. 3).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="h-11 w-full rounded-[1rem] sm:w-auto">
              <a href="/app/report">
                Ouvrir le reporting
                <ArrowRight className="size-4" />
              </a>
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {activeMembership && canManageMemberships ? (
        <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
          <CardHeader className="gap-3">
            <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
              Configuration
            </Badge>
            <div className="space-y-2">
              <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
                Configuration opérationnelle
              </CardTitle>
              <CardDescription className="text-sm leading-6">
                Consultez et modifiez les pôles, sujets et descriptions de votre établissement
                actif.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3 rounded-[1.15rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-3 text-sm text-muted-foreground">
              <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
                <ClipboardCheck className="size-4" />
              </span>
              <span>{activeMembership.establishment_name}</span>
            </div>
            <Button
              type="button"
              className="h-11 rounded-[1rem]"
              onClick={() => onNavigate?.('/app/operational-config')}
            >
              Modifier l’onboarding
              <ArrowRight className="size-4" />
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {activeMembership ? (
        canManageMemberships ? (
          <>
            <MembershipManagementCard
              actorRole={actorRole}
              errorMessage={membershipMutationError}
              isDeactivating={deactivateMutation.isPending}
              isLoadingList={membershipsQuery.isPending}
              isLoadingMembership={membershipDetailQuery.isPending}
              isLoadingTaxonomy={taxonomyQuery.isPending}
              isSaving={updateMutation.isPending}
              memberships={membershipList}
              onDeactivate={handleDeactivateMembership}
              onRoleChange={handleRoleChange}
              onSave={handleSaveMembership}
              onScopesChange={handleScopesChange}
              onSelectMembership={handleSelectMembership}
              roleDraft={roleDraft}
              scopeTree={scopeTree}
              scopeTaxonomyError={scopeTaxonomyError}
              selectedMembership={selectedMembership}
              selectedMembershipId={effectiveSelectedMembershipId}
              selectedScopes={selectedScopes}
            />
            <MembershipInviteCard establishmentId={activeMembership.establishment_id} />
          </>
        ) : (
          <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
            <CardHeader className="gap-3">
              <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
                Memberships
              </Badge>
              <div className="space-y-2">
                <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
                  Membership management unavailable
                </CardTitle>
                <CardDescription className="text-sm leading-6">
                  Your current role is{' '}
                  <span className="font-semibold text-foreground">{activeMembership.role}</span>.
                  Only owners and directors can manage memberships or send invitations.
                </CardDescription>
              </div>
            </CardHeader>
          </Card>
        )
      ) : (
        <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
          <CardHeader className="gap-3">
            <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
              Establishment
            </Badge>
            <div className="space-y-2">
              <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
                Select an establishment to continue
              </CardTitle>
              <CardDescription className="text-sm leading-6">
                Choose one establishment to view its summary and available management tools.
              </CardDescription>
            </div>
          </CardHeader>
        </Card>
      )}
    </div>
  )
}
