import { useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/app/auth-provider'
import {
  canCreateEstablishmentFromBootstrapHints,
  canManageOrganizationFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { getAuthenticatedLandingPath } from '@/features/auth/lib/authenticated-landing'
import { buildOnboardingUrlFromIds } from '@/features/auth/lib/pending-onboarding'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  useCreateOrganizationEstablishmentMutation,
  useInviteOrganizationOwnerMutation,
  useOrganizationEstablishmentsQuery,
  useOrganizationMemberFilterOptionsQuery,
  useOrganizationMembersQuery,
  useOrganizationOverviewQuery,
  useOrganizationOwnersQuery,
} from '../hooks'
import { resolveUniqueOrganizationId } from '../lib/resolve-unique-organization-id'
import type {
  OrganizationAdminOwner,
  OrganizationMemberListFilters,
  OrganizationTab,
} from '../types'
import { CreateEstablishmentSheet, InviteOwnerSheet } from '../components/organization-action-sheets'
import { OrganizationEstablishmentsTab } from '../components/organization-establishments-tab'
import { OrganizationMembersTab } from '../components/organization-members-tab'
import { OrganizationOwnersTab } from '../components/organization-owners-tab'
import { OrganizationTabs } from '../components/organization-tabs'

type OrganizationPageProps = {
  onNavigate: (path: string, options?: { replace?: boolean }) => void
}

export function OrganizationPage({ onNavigate }: OrganizationPageProps) {
  const { bootstrap, isBootstrapping, isReady } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const canManageOrganization = canManageOrganizationFromBootstrapHints(permissionHints)
  const canCreateEstablishment = canCreateEstablishmentFromBootstrapHints(permissionHints)

  const orgResolution = useMemo(() => resolveUniqueOrganizationId(bootstrap), [bootstrap])
  const organizationId = orgResolution.ok ? orgResolution.organizationId : null

  const [activeTab, setActiveTab] = useState<OrganizationTab>('establishments')
  const [memberFilters, setMemberFilters] = useState<OrganizationMemberListFilters>({})
  const [createOpen, setCreateOpen] = useState(false)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [resendingUserId, setResendingUserId] = useState<string | null>(null)

  const overviewQuery = useOrganizationOverviewQuery(organizationId)
  const establishmentsQuery = useOrganizationEstablishmentsQuery(organizationId)
  const membersQuery = useOrganizationMembersQuery(organizationId, memberFilters)
  const filterOptionsQuery = useOrganizationMemberFilterOptionsQuery(organizationId)
  const ownersQuery = useOrganizationOwnersQuery(organizationId)

  const createMutation = useCreateOrganizationEstablishmentMutation(organizationId ?? '')
  const inviteMutation = useInviteOrganizationOwnerMutation(organizationId ?? '')

  useEffect(() => {
    if (!isReady || isBootstrapping) {
      return
    }

    if (!canManageOrganization) {
      onNavigate(getAuthenticatedLandingPath(bootstrap) ?? '/reporting', { replace: true })
    }
  }, [bootstrap, canManageOrganization, isBootstrapping, isReady, onNavigate])

  if (!isReady || isBootstrapping) {
    return <p className={cn('text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!canManageOrganization) {
    return <p className={cn('text-sm', terrain.muted)}>Redirection...</p>
  }

  if (orgResolution.ok === false) {
    const message =
      orgResolution.reason === 'ambiguous'
        ? 'Plusieurs organisations sont associées à ce compte. Contactez le support.'
        : 'Aucune organisation gérable n’a été trouvée.'
    return <p className={cn('text-sm', terrain.muted)}>{message}</p>
  }

  const overview = overviewQuery.data

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold tracking-tight text-[#1a1a1a]">
          Gestion de l&apos;organisation
        </h2>
        {overview ? (
          <>
            <p className="text-base font-medium text-[#1a1a1a]">{overview.name}</p>
            <p className={cn('text-sm', terrain.muted)}>
              {overview.active_establishment_count} établissements actifs ·{' '}
              {overview.draft_establishment_count} en configuration
            </p>
          </>
        ) : overviewQuery.isLoading ? (
          <p className={cn('text-sm', terrain.muted)}>Chargement…</p>
        ) : (
          <p className="text-sm text-red-600">Impossible de charger l’organisation.</p>
        )}
      </header>

      <OrganizationTabs activeTab={activeTab} onChange={setActiveTab} />

      <div
        role="tabpanel"
        id={`organization-panel-${activeTab}`}
        aria-labelledby={`organization-tab-${activeTab}`}
      >
        {activeTab === 'establishments' ? (
          <OrganizationEstablishmentsTab
            establishments={establishmentsQuery.data?.results ?? []}
            canCreate={canCreateEstablishment}
            onManage={(establishmentId) =>
              onNavigate(`/organization/establishments/${establishmentId}`)
            }
            onResume={(establishmentId, sessionId) =>
              onNavigate(buildOnboardingUrlFromIds(establishmentId, sessionId))
            }
            onCreate={() => {
              setCreateError(null)
              setCreateOpen(true)
            }}
          />
        ) : null}

        {activeTab === 'members' ? (
          <OrganizationMembersTab
            members={membersQuery.data?.results ?? []}
            filterOptions={filterOptionsQuery.data}
            filters={memberFilters}
            onFiltersChange={setMemberFilters}
            onOpenEstablishment={(establishmentId) =>
              onNavigate(`/organization/establishments/${establishmentId}`)
            }
            isLoading={membersQuery.isLoading}
          />
        ) : null}

        {activeTab === 'owners' ? (
          <OrganizationOwnersTab
            owners={ownersQuery.data?.results ?? []}
            isLoading={ownersQuery.isLoading}
            onInvite={() => {
              setInviteError(null)
              setInviteOpen(true)
            }}
            isResendingUserId={resendingUserId}
            onResend={async (owner: OrganizationAdminOwner) => {
              if (!organizationId) return
              setResendingUserId(owner.user_id)
              setInviteError(null)
              try {
                await inviteMutation.mutateAsync({
                  email: owner.email,
                  first_name: owner.first_name || 'Owner',
                  last_name: owner.last_name || 'Invite',
                })
              } catch (error) {
                setInviteError(
                  error instanceof Error ? error.message : 'Renvoi impossible.',
                )
              } finally {
                setResendingUserId(null)
              }
            }}
          />
        ) : null}
      </div>

      {inviteError && !inviteOpen ? (
        <p className="text-sm text-red-600">{inviteError}</p>
      ) : null}

      <CreateEstablishmentSheet
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        isSubmitting={createMutation.isPending}
        errorMessage={createError}
        onSubmit={async (name) => {
          if (!organizationId) return
          setCreateError(null)
          try {
            const created = await createMutation.mutateAsync(name)
            setCreateOpen(false)
            onNavigate(
              buildOnboardingUrlFromIds(created.establishment_id, created.onboarding_session_id),
            )
          } catch (error) {
            setCreateError(error instanceof Error ? error.message : 'Création impossible.')
          }
        }}
      />

      <InviteOwnerSheet
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        isSubmitting={inviteMutation.isPending}
        errorMessage={inviteError}
        onSubmit={async (input) => {
          if (!organizationId) return
          setInviteError(null)
          try {
            await inviteMutation.mutateAsync(input)
            setInviteOpen(false)
          } catch (error) {
            setInviteError(error instanceof Error ? error.message : 'Invitation impossible.')
          }
        }}
      />
    </div>
  )
}
