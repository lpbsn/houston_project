import { useId, useState, type ComponentType } from 'react'
import { Building2, ChevronRight, ClipboardCheck, Users } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import {
  HoustonBadge,
  TerrainCard,
  TerrainSectionLabel,
} from '@/components/ui/terrain'
import {
  canAccessManagementSpace,
  canManageRuntimeConfigFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { toRoleEnum } from '@/features/auth/lib/role'
import type { RoleEnum } from '@/features/auth/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const ROLE_DISPLAY_LABELS: Record<RoleEnum, string> = {
  owner: 'Propriétaire',
  director: 'Directeur',
  manager: 'Manager',
  staff: 'Équipe',
}

type ProfilePageProps = {
  onNavigate?: (pathname: string) => void
  onSignOut?: () => void
  isLoggingOut?: boolean
}

function readOptionalUserName(user: unknown, key: 'first_name' | 'last_name') {
  if (!user || typeof user !== 'object') {
    return null
  }

  const value = (user as Record<string, unknown>)[key]
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null
}

function formatRoleDisplay(role: RoleEnum): string {
  return ROLE_DISPLAY_LABELS[role]
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

function buildRoleEstablishmentLine(
  role: RoleEnum | null,
  establishmentName: string | null | undefined,
) {
  if (!role && !establishmentName) {
    return null
  }

  const roleLabel = role ? formatRoleDisplay(role) : null
  if (roleLabel && establishmentName) {
    return `${roleLabel} · ${establishmentName}`
  }

  return roleLabel ?? establishmentName ?? null
}

// placeholder — no API persistence
function ProfilePlaceholderSwitch({
  label,
  checked,
  onCheckedChange,
}: {
  label: string
  checked: boolean
  onCheckedChange: (checked: boolean) => void
}) {
  const labelId = useId()

  return (
    <div className="flex min-h-11 items-center justify-between gap-3 px-4 py-3.5">
      <span id={labelId} className="text-sm text-[#1a1a1a]">
        {label}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={labelId}
        className={cn(
          'relative h-7 w-12 shrink-0 rounded-full transition-colors',
          checked ? 'bg-[#1D9E75]' : 'bg-[#E8E6DF]',
        )}
        onClick={() => onCheckedChange(!checked)}
      >
        <span
          aria-hidden
          className={cn(
            'absolute top-0.5 left-0.5 h-6 w-6 rounded-full bg-white shadow-sm transition-transform',
            checked ? 'translate-x-5' : 'translate-x-0',
          )}
        />
      </button>
    </div>
  )
}

type ProfileManagementNavCardProps = {
  icon: ComponentType<{ className?: string }>
  iconClassName: string
  title: string
  subtitle: string
  onClick: () => void
}

function ProfileManagementNavCard({
  icon: Icon,
  iconClassName,
  title,
  subtitle,
  onClick,
}: ProfileManagementNavCardProps) {
  return (
    <button
      type="button"
      className="w-full text-left active:opacity-90"
      onClick={onClick}
    >
      <TerrainCard className="flex min-h-11 items-center gap-3 p-4">
        <span
          className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
            iconClassName,
          )}
          aria-hidden
        >
          <Icon className="h-5 w-5" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-[#1a1a1a]">{title}</span>
          <span className={cn('mt-0.5 block text-xs', terrain.muted)}>{subtitle}</span>
        </span>
        <ChevronRight className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
      </TerrainCard>
    </button>
  )
}

export function ProfilePage({ onNavigate, onSignOut, isLoggingOut = false }: ProfilePageProps) {
  const { activeMembership, bootstrap, user, isBootstrapping, isReady } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)

  const firstName = readOptionalUserName(user, 'first_name')
  const lastName = readOptionalUserName(user, 'last_name')
  const identityLabel = user ? (user.email ?? user.username) : null
  const role = toRoleEnum(activeMembership?.role)
  const canAccessManagement = canAccessManagementSpace(permissionHints)
  const canManageRuntimeConfig = canManageRuntimeConfigFromBootstrapHints(permissionHints)
  const canShowChecklistsNav = Boolean(activeMembership && role)
  const displayName = buildDisplayName(firstName, lastName, identityLabel)
  const initials = buildInitials(firstName, lastName, identityLabel)
  const roleEstablishmentLine = buildRoleEstablishmentLine(
    role,
    activeMembership?.establishment_name,
  )

  // placeholder — no API persistence
  const [signalNotificationsEnabled, setSignalNotificationsEnabled] = useState(true)
  const [executionNotificationsEnabled, setExecutionNotificationsEnabled] = useState(true)

  if (!isReady || isBootstrapping) {
    return (
      <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement du profil...</p>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-3 pb-4 pt-3">
      <TerrainCard className="flex items-center gap-3 p-4">
        <div
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-[#BFCFFF] text-lg font-bold text-[#1B4FD8]"
          aria-hidden
        >
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold text-[#1a1a1a]">{displayName}</p>
          {roleEstablishmentLine ? (
            <p className={cn('mt-0.5 truncate text-sm', terrain.muted)}>{roleEstablishmentLine}</p>
          ) : null}
          {role ? (
            <HoustonBadge variant="blue" className="mt-2">
              {formatRoleDisplay(role).toUpperCase()}
            </HoustonBadge>
          ) : null}
        </div>
      </TerrainCard>

      <div className="space-y-2">
        <TerrainSectionLabel>Mon compte</TerrainSectionLabel>
        <TerrainCard className="divide-y divide-[#E8E6DF] p-0">
          <ProfilePlaceholderSwitch
            label="Notifications signaux"
            checked={signalNotificationsEnabled}
            onCheckedChange={setSignalNotificationsEnabled}
          />
          <ProfilePlaceholderSwitch
            label="Notifications exécutions"
            checked={executionNotificationsEnabled}
            onCheckedChange={setExecutionNotificationsEnabled}
          />
          <div className="flex min-h-11 items-center justify-between gap-3 px-4 py-3.5">
            <span className="text-sm text-[#1a1a1a]">Langue</span>
            <span className={cn('text-sm', terrain.muted)}>Français</span>
          </div>
        </TerrainCard>
      </div>

      {canAccessManagement ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2 px-0.5">
            <TerrainSectionLabel dotVariant="primary" className="py-0">
              Gestion de l&apos;établissement
            </TerrainSectionLabel>
            {role ? (
              <HoustonBadge variant="blue">{formatRoleDisplay(role).toUpperCase()}</HoustonBadge>
            ) : null}
          </div>

          <div className="space-y-2">
            {canManageRuntimeConfig ? (
              <ProfileManagementNavCard
                icon={Building2}
                iconClassName="bg-[#EEF2FF] text-[#1B4FD8]"
                title="Établissement"
                subtitle="Pôles d'activités et sujets"
                onClick={() => onNavigate?.('/app/operational-config')}
              />
            ) : null}

            {canShowChecklistsNav ? (
              <ProfileManagementNavCard
                icon={ClipboardCheck}
                iconClassName="bg-[#FFF4E0] text-[#EF9F27]"
                title="Listes"
                subtitle="Gérer, modifier, désactiver"
                onClick={() => onNavigate?.('/checklists')}
              />
            ) : null}

            <ProfileManagementNavCard
              icon={Users}
              iconClassName="bg-[#E8F7F0] text-[#1D9E75]"
              title="Équipe"
              subtitle="Ajouter, supprimer, gérer les autorisations"
              onClick={() => onNavigate?.('/team')}
            />
          </div>
        </div>
      ) : null}

      {onSignOut ? (
        <TerrainCard padding="sm">
          <button
            type="button"
            className={cn(
              'flex min-h-11 w-full items-center justify-center text-sm font-medium text-[#E24B4A]',
              isLoggingOut && 'opacity-60',
            )}
            disabled={isLoggingOut}
            onClick={onSignOut}
          >
            {isLoggingOut ? 'Déconnexion...' : 'Se déconnecter'}
          </button>
        </TerrainCard>
      ) : null}
    </div>
  )
}
