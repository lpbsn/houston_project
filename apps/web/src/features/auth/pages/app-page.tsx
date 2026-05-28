import { startTransition, type ReactNode, useDeferredValue, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Sparkles, UserRound } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  deactivateMembership,
  getMembership,
  listMemberships,
  membershipDetailQueryKey,
  membershipListQueryKey,
  scopedUserSearchQueryKey,
  searchUsers,
  switchEstablishment,
  updateMembership,
} from '@/features/auth/api'
import { EstablishmentSelectorCard } from '@/features/auth/components/establishment-selector-card'
import { MembershipManagementCard } from '@/features/auth/components/membership-management-card'
import { ScopedUserSearchCard } from '@/features/auth/components/scoped-user-search-card'
import type {
  EstablishmentMembershipResponse,
  MembershipUpdateRequest,
  RoleEnum,
  ScopedUserSearchResult,
} from '@/features/auth/types'

const MANAGEABLE_ROLES = new Set<RoleEnum>(['owner', 'director'])
const ROLE_OPTIONS: RoleEnum[] = ['owner', 'director', 'manager', 'staff']
const EMPTY_MEMBERSHIPS: EstablishmentMembershipResponse[] = []
const EMPTY_SEARCH_RESULTS: ScopedUserSearchResult[] = []

function normalizeRole(role: string | null | undefined): RoleEnum {
  return ROLE_OPTIONS.find((candidate) => candidate === role) ?? 'staff'
}

function parseDomainDraft(value: string) {
  return value
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
}

function toErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallback
}

export function AppPage() {
  const queryClient = useQueryClient()
  const { activeMembership, memberships, user } = useAuth()
  const [pendingEstablishmentId, setPendingEstablishmentId] = useState<string | null>(null)
  const [selectorError, setSelectorError] = useState<string | null>(null)
  const [selectedMembershipId, setSelectedMembershipId] = useState<string | null>(null)
  const [editorState, setEditorState] = useState<{
    domainDraft: string
    membershipId: string | null
    roleDraft: RoleEnum
  }>({
    membershipId: null,
    roleDraft: 'staff',
    domainDraft: '',
  })
  const [membershipMutationError, setMembershipMutationError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const deferredSearchQuery = useDeferredValue(searchQuery.trim())

  const activeEstablishmentId = activeMembership?.establishment_id ?? null
  const canManageMemberships = MANAGEABLE_ROLES.has(normalizeRole(activeMembership?.role))
  const needsEstablishmentSelection = memberships.length > 1 && !activeMembership
  const workspaceLabel = activeMembership?.establishment_name ?? 'No establishment selected'
  const workspaceDescription = activeMembership
    ? `${activeMembership.organization_name} · ${activeMembership.role}`
    : 'Choose one establishment to unlock the backend-owned workspace context for this session.'

  const switchMutation = useMutation({
    mutationFn: switchEstablishment,
  })

  const membershipsQuery = useQuery({
    queryKey: activeEstablishmentId
      ? membershipListQueryKey(activeEstablishmentId)
      : ['workspace', 'memberships', 'idle'],
    queryFn: () => listMemberships(activeEstablishmentId!),
    enabled: Boolean(activeEstablishmentId && canManageMemberships),
    staleTime: 30_000,
  })

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
      setEditorState({
        membershipId: membership.id,
        roleDraft: normalizeRole(membership.role),
        domainDraft: membership.operational_domains.join(', '),
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
    onSuccess: async (membership) => {
      if (!activeEstablishmentId) {
        return
      }

      await queryClient.invalidateQueries({ queryKey: membershipListQueryKey(activeEstablishmentId) })
      await queryClient.invalidateQueries({
        queryKey: membershipDetailQueryKey(activeEstablishmentId, membership.id),
      })
      startTransition(() => {
        setSelectedMembershipId(null)
        setEditorState({
          membershipId: null,
          roleDraft: 'staff',
          domainDraft: '',
        })
        setMembershipMutationError(null)
      })
    },
  })

  const scopedUserSearchQuery = useQuery({
    queryKey: activeEstablishmentId
      ? scopedUserSearchQueryKey(activeEstablishmentId, deferredSearchQuery)
      : ['workspace', 'user-search', 'idle'],
    queryFn: () => searchUsers(activeEstablishmentId!, deferredSearchQuery),
    enabled: Boolean(activeEstablishmentId && deferredSearchQuery.length >= 2),
    staleTime: 20_000,
  })

  const selectedMembership = membershipDetailQuery.data ?? null
  const searchResults = scopedUserSearchQuery.data ?? EMPTY_SEARCH_RESULTS
  const roleDraft =
    editorState.membershipId === selectedMembership?.id
      ? editorState.roleDraft
      : normalizeRole(selectedMembership?.role)
  const domainDraft =
    editorState.membershipId === selectedMembership?.id
      ? editorState.domainDraft
      : selectedMembership?.operational_domains.join(', ') ?? ''

  const identityLabel = useMemo(() => {
    if (!user) {
      return 'Unknown user'
    }

    return user.email ?? `@${user.username}`
  }, [user])

  const knownDomainKeys = useMemo(() => {
    const keys = new Set<string>()

    for (const membership of membershipList) {
      for (const key of membership.operational_domains) {
        keys.add(key)
      }
    }

    return Array.from(keys).sort()
  }, [membershipList])

  const searchHint = activeEstablishmentId
    ? deferredSearchQuery.length >= 2
      ? `Searching ${workspaceLabel} for “${deferredSearchQuery}”.`
      : 'Type at least two characters. Search stays inside the currently selected establishment.'
    : 'Select an establishment first. Search cannot run without a backend-owned active workspace.'

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
          domainDraft: '',
        })
        setMembershipMutationError(null)
        setSearchQuery('')
      })
    } catch (error) {
      setSelectorError(toErrorMessage(error, 'We could not switch this establishment.'))
    } finally {
      setPendingEstablishmentId(null)
    }
  }

  async function handleSaveMembership() {
    const nextInput: MembershipUpdateRequest = {
      role: roleDraft,
      operational_domains: parseDomainDraft(domainDraft),
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
      domainDraft,
    })
  }

  function handleDomainDraftChange(value: string) {
    setEditorState({
      membershipId: selectedMembership?.id ?? effectiveSelectedMembershipId,
      roleDraft,
      domainDraft: value,
    })
  }

  function handleSelectMembership(membershipId: string) {
    setSelectedMembershipId(membershipId)
    setEditorState({
      membershipId: null,
      roleDraft: 'staff',
      domainDraft: '',
    })
    setMembershipMutationError(null)
  }

  return (
    <div className="space-y-4 sm:space-y-5">
      <Card className="rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
        <CardHeader className="gap-3">
          <div className="flex flex-wrap gap-2">
            <Badge className="bg-[color:var(--primary)] text-primary-foreground">Live session</Badge>
            <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
              Backend-owned context
            </Badge>
          </div>
          <div className="space-y-2">
            <CardTitle className="text-[1.7rem] font-black tracking-[-0.06em]">
              {workspaceLabel}
            </CardTitle>
            <CardDescription className="text-sm leading-6">{workspaceDescription}</CardDescription>
          </div>
        </CardHeader>

        <CardContent className="grid gap-3 sm:grid-cols-3">
          <SummaryTile
            icon={<UserRound className="size-4" />}
            label="Identity"
            value={identityLabel}
            supporting={user ? user.username : 'No user loaded'}
          />
          <SummaryTile
            icon={<Building2 className="size-4" />}
            label="Memberships"
            value={`${memberships.length}`}
            supporting={
              memberships.length === 1
                ? 'One active establishment'
                : `${memberships.length} available establishments`
            }
          />
          <SummaryTile
            icon={<Sparkles className="size-4" />}
            label="Domains"
            value={activeMembership ? `${activeMembership.operational_domains.length}` : '0'}
            supporting={
              activeMembership
                ? activeMembership.operational_domains.join(', ') || 'No domains assigned'
                : 'Selection required first'
            }
          />
        </CardContent>
      </Card>

      {needsEstablishmentSelection ? (
        <EstablishmentSelectorCard
          memberships={memberships}
          pendingEstablishmentId={pendingEstablishmentId}
          onSelect={handleSelectEstablishment}
          errorMessage={selectorError}
        />
      ) : null}

      <ScopedUserSearchCard
        query={searchQuery}
        onQueryChange={setSearchQuery}
        results={searchResults}
        isSearching={scopedUserSearchQuery.isFetching}
        errorMessage={
          scopedUserSearchQuery.error
            ? toErrorMessage(scopedUserSearchQuery.error, 'User search is unavailable.')
            : null
        }
        hint={searchHint}
      />

      {activeMembership ? (
        canManageMemberships ? (
          <MembershipManagementCard
            domainDraft={domainDraft}
            errorMessage={membershipMutationError}
            isDeactivating={deactivateMutation.isPending}
            isLoadingList={membershipsQuery.isPending}
            isLoadingMembership={membershipDetailQuery.isPending}
            isSaving={updateMutation.isPending}
            memberships={membershipList}
            onDeactivate={handleDeactivateMembership}
            onDomainDraftChange={handleDomainDraftChange}
            onRoleChange={handleRoleChange}
            onSave={handleSaveMembership}
            onSelectMembership={handleSelectMembership}
            roleDraft={roleDraft}
            selectedMembership={selectedMembership}
            selectedMembershipId={effectiveSelectedMembershipId}
          />
        ) : (
          <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
            <CardHeader className="gap-3">
              <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
                Memberships
              </Badge>
              <div className="space-y-2">
                <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
                  Membership editing stays limited
                </CardTitle>
                <CardDescription className="text-sm leading-6">
                  This shell only opens role and domain editing for owner and director contexts.
                  The backend still remains the authority for every permission decision.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <div className="rounded-[1.15rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-4 text-sm text-muted-foreground">
                Your current role is <span className="font-semibold text-foreground">{activeMembership.role}</span>.
                Scoped user search is still available above.
              </div>
            </CardContent>
          </Card>
        )
      ) : (
        <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
          <CardHeader className="gap-3">
            <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
              Workspace context
            </Badge>
            <div className="space-y-2">
              <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
                Select one establishment to continue
              </CardTitle>
              <CardDescription className="text-sm leading-6">
                Membership management and scoped search stay unavailable until the backend session
                exposes one active membership.
              </CardDescription>
            </div>
          </CardHeader>
        </Card>
      )}

      {canManageMemberships && knownDomainKeys.length > 0 ? (
        <div className="rounded-[1.15rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-3 text-sm text-muted-foreground">
          Known active domain keys in this workspace: {knownDomainKeys.join(', ')}
        </div>
      ) : null}
    </div>
  )
}

function SummaryTile({
  icon,
  label,
  supporting,
  value,
}: {
  icon: ReactNode
  label: string
  supporting: string
  value: string
}) {
  return (
    <div className="rounded-[1.35rem] border border-[#ece5da] bg-white px-4 py-4 shadow-[0_14px_34px_-32px_rgba(46,72,173,0.22)]">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
          {icon}
        </span>
        {label}
      </div>
      <div className="text-[1.55rem] font-black tracking-[-0.05em] text-foreground">{value}</div>
      <div className="mt-1 text-sm leading-6 text-muted-foreground">{supporting}</div>
    </div>
  )
}
