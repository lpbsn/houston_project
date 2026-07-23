import { useEffect, useState } from 'react'

import { useAuth } from '@/app/auth-provider'
import { switchEstablishment } from '@/features/auth/api'
import {
  canManageOrganizationFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { getAuthenticatedLandingPath } from '@/features/auth/lib/authenticated-landing'
import { Button } from '@/components/ui/button'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { EditEstablishmentMemberSheet } from '../components/establishment-admin-edit-member-sheet'
import { InviteEstablishmentMemberSheet } from '../components/establishment-admin-invite-sheet'
import { EstablishmentAdminMembersTab } from '../components/establishment-admin-members-tab'
import { EstablishmentAdminOverviewTab } from '../components/establishment-admin-overview-tab'
import { EstablishmentAdminTabs } from '../components/establishment-admin-tabs'
import {
  useActivateEstablishmentAdminMembershipMutation,
  useDeactivateEstablishmentAdminMembershipMutation,
  useEstablishmentAdminMemberFilterOptionsQuery,
  useEstablishmentAdminMembershipsQuery,
  useEstablishmentAdminOverviewQuery,
  useInviteEstablishmentAdminMembershipMutation,
  useUpdateEstablishmentAdminMembershipMutation,
} from '../hooks'
import {
  canAccessEstablishmentAdminPage,
  resolveEstablishmentAdminActorRole,
} from '../lib/can-access-establishment-admin'
import { getEstablishmentAdminInviteTargetRoles } from '../lib/establishment-admin-invite-roles'
import { planOpenOperationalConfig } from '../lib/operational-config-navigation'
import type {
  EstablishmentAdminMemberListFilters,
  EstablishmentAdminMembership,
  EstablishmentAdminTab,
} from '../types'

type OrganizationEstablishmentPageProps = {
  establishmentId: string
  onNavigate: (path: string, options?: { replace?: boolean }) => void
}

export function OrganizationEstablishmentPage({
  establishmentId,
  onNavigate,
}: OrganizationEstablishmentPageProps) {
  const { activeMembership, bootstrap, isBootstrapping, isReady } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const canManageOrganization = canManageOrganizationFromBootstrapHints(permissionHints)
  const canAccess = canAccessEstablishmentAdminPage({
    canManageOrganization,
    memberships: bootstrap?.memberships,
    establishmentId,
  })
  const actorRole = resolveEstablishmentAdminActorRole({
    canManageOrganization,
    memberships: bootstrap?.memberships,
    establishmentId,
  })
  const inviteRoles = getEstablishmentAdminInviteTargetRoles(actorRole)

  const [activeTab, setActiveTab] = useState<EstablishmentAdminTab>('overview')
  const [memberFilters, setMemberFilters] = useState<EstablishmentAdminMemberListFilters>({})
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [editMember, setEditMember] = useState<EstablishmentAdminMembership | null>(null)
  const [editError, setEditError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [opsError, setOpsError] = useState<string | null>(null)
  const [opsPending, setOpsPending] = useState(false)
  const [pendingMembershipId, setPendingMembershipId] = useState<string | null>(null)

  const overviewQuery = useEstablishmentAdminOverviewQuery(canAccess ? establishmentId : null)
  const membershipsQuery = useEstablishmentAdminMembershipsQuery(
    canAccess ? establishmentId : null,
    memberFilters,
  )
  const filterOptionsQuery = useEstablishmentAdminMemberFilterOptionsQuery(
    canAccess ? establishmentId : null,
  )

  const inviteMutation = useInviteEstablishmentAdminMembershipMutation(establishmentId)
  const updateMutation = useUpdateEstablishmentAdminMembershipMutation(establishmentId)
  const deactivateMutation = useDeactivateEstablishmentAdminMembershipMutation(establishmentId)
  const activateMutation = useActivateEstablishmentAdminMembershipMutation(establishmentId)

  useEffect(() => {
    if (!isReady || isBootstrapping) {
      return
    }

    if (!canAccess) {
      if (canManageOrganization) {
        onNavigate('/organization', { replace: true })
        return
      }
      onNavigate(getAuthenticatedLandingPath(bootstrap) ?? '/reporting', { replace: true })
    }
  }, [
    bootstrap,
    canAccess,
    canManageOrganization,
    isBootstrapping,
    isReady,
    onNavigate,
  ])

  useEffect(() => {
    if (!overviewQuery.isError) {
      return
    }
    if (canManageOrganization) {
      onNavigate('/organization', { replace: true })
      return
    }
    onNavigate(getAuthenticatedLandingPath(bootstrap) ?? '/reporting', { replace: true })
  }, [bootstrap, canManageOrganization, onNavigate, overviewQuery.isError])

  async function handleOpenOperationalConfig() {
    setOpsError(null)
    const plan = planOpenOperationalConfig({
      targetEstablishmentId: establishmentId,
      activeEstablishmentId: activeMembership?.establishment_id,
    })

    if (plan.kind === 'already_selected') {
      onNavigate(plan.path)
      return
    }

    setOpsPending(true)
    try {
      await switchEstablishment({ establishment_id: plan.establishmentId })
      onNavigate(plan.path)
    } catch {
      setOpsError('Impossible de basculer vers cet établissement.')
    } finally {
      setOpsPending(false)
    }
  }

  if (!isReady || isBootstrapping) {
    return <p className={cn('text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!canAccess) {
    return <p className={cn('text-sm', terrain.muted)}>Redirection...</p>
  }

  const overview = overviewQuery.data

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <Button
            type="button"
            variant="ghost"
            className="h-auto px-0 text-sm text-[#1B4FD8]"
            onClick={() => onNavigate('/organization')}
          >
            ← Organisation
          </Button>
          <h2 className="text-2xl font-semibold tracking-tight text-[#1a1a1a]">
            {overview?.name ?? 'Établissement'}
          </h2>
          {overview ? (
            <p className={cn('text-sm', terrain.muted)}>{overview.organization_name}</p>
          ) : null}
        </div>
        <div className="flex flex-col items-stretch gap-2 sm:items-end">
          <Button
            type="button"
            variant="outline"
            disabled={opsPending}
            onClick={() => {
              void handleOpenOperationalConfig()
            }}
          >
            Configuration opérationnelle
          </Button>
          {opsError ? <p className="text-sm text-red-600">{opsError}</p> : null}
        </div>
      </header>

      <EstablishmentAdminTabs activeTab={activeTab} onChange={setActiveTab} />

      <div
        role="tabpanel"
        id={`establishment-admin-panel-${activeTab}`}
        aria-labelledby={`establishment-admin-tab-${activeTab}`}
      >
        {activeTab === 'overview' ? (
          overviewQuery.isLoading ? (
            <p className={cn('text-sm', terrain.muted)}>Chargement…</p>
          ) : overview ? (
            <EstablishmentAdminOverviewTab overview={overview} />
          ) : (
            <p className="text-sm text-red-600">Impossible de charger la vue d’ensemble.</p>
          )
        ) : (
          <EstablishmentAdminMembersTab
            members={membershipsQuery.data?.results ?? []}
            filterOptions={filterOptionsQuery.data}
            filters={memberFilters}
            onFiltersChange={setMemberFilters}
            onInvite={() => {
              setInviteError(null)
              setInviteOpen(true)
            }}
            canInvite={inviteRoles.length > 0}
            pendingMembershipId={pendingMembershipId}
            isLoading={membershipsQuery.isLoading}
            actionError={actionError}
            onDeactivate={async (membershipId) => {
              setActionError(null)
              setPendingMembershipId(membershipId)
              try {
                await deactivateMutation.mutateAsync(membershipId)
              } catch (error) {
                setActionError(
                  error instanceof Error ? error.message : 'Désactivation impossible.',
                )
              } finally {
                setPendingMembershipId(null)
              }
            }}
            onActivate={async (membershipId) => {
              setActionError(null)
              setPendingMembershipId(membershipId)
              try {
                await activateMutation.mutateAsync(membershipId)
              } catch (error) {
                setActionError(
                  error instanceof Error ? error.message : 'Réactivation impossible.',
                )
              } finally {
                setPendingMembershipId(null)
              }
            }}
            onEdit={(member) => {
              setEditError(null)
              setEditMember(member)
            }}
          />
        )}
      </div>

      <InviteEstablishmentMemberSheet
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        allowedRoles={inviteRoles}
        filterOptions={filterOptionsQuery.data}
        isSubmitting={inviteMutation.isPending}
        errorMessage={inviteError}
        onSubmit={async (input) => {
          setInviteError(null)
          try {
            await inviteMutation.mutateAsync({
              email: input.email,
              first_name: input.first_name,
              last_name: input.last_name,
              role: input.role,
              scopes: input.scopes,
            })
            setInviteOpen(false)
          } catch (error) {
            setInviteError(
              error instanceof Error ? error.message : 'Invitation impossible.',
            )
          }
        }}
      />

      <EditEstablishmentMemberSheet
        open={editMember !== null}
        member={editMember}
        onClose={() => setEditMember(null)}
        allowedRoles={inviteRoles}
        filterOptions={filterOptionsQuery.data}
        isSubmitting={updateMutation.isPending}
        errorMessage={editError}
        onSubmit={async (body) => {
          if (!editMember) {
            return
          }
          setEditError(null)
          try {
            await updateMutation.mutateAsync({
              membershipId: editMember.id,
              body,
            })
            setEditMember(null)
          } catch (error) {
            setEditError(
              error instanceof Error ? error.message : 'Modification impossible.',
            )
          }
        }}
      />
    </div>
  )
}
