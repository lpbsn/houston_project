import { useAuth } from '@/app/auth-provider'
import {
  TerrainCard,
  TerrainFieldLabel,
  TerrainSectionLabel,
} from '@/components/layout/terrain-card'
import { Button } from '@/components/ui/button'
import { canSeeInviteMemberButton } from '@/features/auth/lib/invitation-rbac'
import type { RoleEnum } from '@/features/auth/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const MANAGEMENT_ROLES = new Set(['owner', 'director', 'manager'])
const INVITATION_ROLES: RoleEnum[] = ['owner', 'director', 'manager', 'staff']

const ROLE_DISPLAY_LABELS: Record<RoleEnum, string> = {
  owner: 'Propriétaire',
  director: 'Directeur',
  manager: 'Manager',
  staff: 'Équipe',
}

const MEMBERSHIP_STATUS_LABELS: Record<string, string> = {
  active: 'Actif',
  inactive: 'Inactif',
}

function formatRoleDisplay(role: RoleEnum): string {
  return ROLE_DISPLAY_LABELS[role]
}

function formatMembershipStatusDisplay(status: string): string {
  return MEMBERSHIP_STATUS_LABELS[status] ?? status
}

type ProfilePageProps = {
  onNavigate?: (pathname: string) => void
  onSignOut?: () => void
  isLoggingOut?: boolean
}

function toRoleEnum(role: string | null | undefined): RoleEnum | null {
  if (!role) {
    return null
  }

  return INVITATION_ROLES.find((candidate) => candidate === role) ?? null
}

function readOptionalUserName(user: unknown, key: 'first_name' | 'last_name') {
  if (!user || typeof user !== 'object') {
    return null
  }

  const value = (user as Record<string, unknown>)[key]
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null
}

function toScopeSummaryText(
  scopeSummary: unknown,
  role: RoleEnum | null,
) {
  if (role === 'owner' || role === 'director') {
    return 'Périmètre complet'
  }

  if (!scopeSummary || typeof scopeSummary !== 'object') {
    return null
  }

  const summary = scopeSummary as Record<string, unknown>
  const businessUnitCount =
    typeof summary.business_unit_count === 'number' ? summary.business_unit_count : null

  if (businessUnitCount === null) {
    return null
  }

  if (businessUnitCount > 0) {
    const label = businessUnitCount === 1 ? 'pôle' : 'pôles'
    return `${businessUnitCount} ${label}`
  }

  return 'Aucun périmètre'
}

function buildDisplayName(
  firstName: string | null,
  lastName: string | null,
  identityLabel: string | null,
): string {
  const parts = [firstName, lastName].filter(Boolean)
  if (parts.length > 0) {
    return parts.join(' ')
  }
  return identityLabel ?? 'Compte'
}

function buildInitials(
  firstName: string | null,
  lastName: string | null,
  identityLabel: string | null,
): string {
  if (firstName && lastName) {
    return `${firstName[0]}${lastName[0]}`.toUpperCase()
  }
  if (firstName) {
    return firstName.slice(0, 2).toUpperCase()
  }
  if (identityLabel) {
    return identityLabel.slice(0, 2).toUpperCase()
  }
  return '?'
}

function ProfileField({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <TerrainFieldLabel>{label}</TerrainFieldLabel>
      <p className="text-sm font-medium text-[#1a1a1a]">{value}</p>
    </div>
  )
}

export function ProfilePage({ onNavigate, onSignOut, isLoggingOut = false }: ProfilePageProps) {
  const { activeMembership, user, isBootstrapping, isReady } = useAuth()

  const firstName = readOptionalUserName(user, 'first_name')
  const lastName = readOptionalUserName(user, 'last_name')
  const identityLabel = user ? (user.email ?? user.username) : null
  const role = toRoleEnum(activeMembership?.role)
  const canAccessManagement = role ? MANAGEMENT_ROLES.has(role) : false
  const canInviteMember = canSeeInviteMemberButton(role)
  const scopeSummary = toScopeSummaryText(activeMembership?.scope_summary, role)
  const displayName = buildDisplayName(firstName, lastName, identityLabel)
  const initials = buildInitials(firstName, lastName, identityLabel)

  if (!isReady || isBootstrapping) {
    return (
      <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement du profil...</p>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col pb-4">
      <header className="flex flex-col items-center gap-2 border-b border-[#E8E6DF] bg-white px-4 py-5">
        <div
          className="flex h-[70px] w-[70px] items-center justify-center rounded-full bg-[#BFCFFF] text-[26px] font-bold text-[#1B4FD8]"
          aria-hidden
        >
          {initials}
        </div>
        <h1 className="text-lg font-semibold text-[#1a1a1a]">{displayName}</h1>
        {role ? (
          <p className={cn('text-sm', terrain.muted)}>{formatRoleDisplay(role)}</p>
        ) : null}
        {activeMembership?.establishment_name ? (
          <span className="rounded-full bg-[#EEF2FF] px-2.5 py-1 text-[11px] font-medium text-[#1B4FD8]">
            {activeMembership.establishment_name}
          </span>
        ) : null}
      </header>

      <div className="space-y-3 px-3 pt-3">
        <TerrainSectionLabel>Compte</TerrainSectionLabel>
        <TerrainCard className="space-y-3">
          {firstName ? <ProfileField label="Prénom" value={firstName} /> : null}
          {lastName ? <ProfileField label="Nom" value={lastName} /> : null}
          {identityLabel ? <ProfileField label="Identifiant" value={identityLabel} /> : null}
        </TerrainCard>

        <TerrainSectionLabel>Établissement</TerrainSectionLabel>
        <TerrainCard className="space-y-3">
          {role ? <ProfileField label="Rôle" value={formatRoleDisplay(role)} /> : null}
          {activeMembership?.establishment_name ? (
            <ProfileField label="Établissement" value={activeMembership.establishment_name} />
          ) : null}
          {activeMembership?.organization_name ? (
            <ProfileField label="Organisation" value={activeMembership.organization_name} />
          ) : null}
          {activeMembership?.status ? (
            <ProfileField
              label="Statut"
              value={formatMembershipStatusDisplay(activeMembership.status)}
            />
          ) : null}
          {scopeSummary ? (
            <ProfileField label="Périmètre opérationnel" value={scopeSummary} />
          ) : null}

          {canAccessManagement ? (
            <Button
              type="button"
              className="mt-1 h-11 w-full rounded-xl bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
              onClick={() => onNavigate?.('/app')}
            >
              Espace gestion
            </Button>
          ) : null}

          {activeMembership && canInviteMember ? (
            <Button
              type="button"
              variant="outline"
              className="h-11 w-full rounded-xl border-[#E8E6DF]"
              onClick={() => onNavigate?.('/team/invite')}
            >
              Inviter un membre
            </Button>
          ) : null}
        </TerrainCard>

        {onSignOut ? (
          <>
            <TerrainSectionLabel className="mt-2">Session</TerrainSectionLabel>
            <TerrainCard padding="sm">
              <button
                type="button"
                className={cn(
                  'w-full py-2 text-left text-sm font-medium text-[#E24B4A]',
                  isLoggingOut && 'opacity-60',
                )}
                disabled={isLoggingOut}
                onClick={onSignOut}
              >
                {isLoggingOut ? 'Déconnexion...' : 'Déconnexion'}
              </button>
            </TerrainCard>
          </>
        ) : null}
      </div>
    </div>
  )
}
