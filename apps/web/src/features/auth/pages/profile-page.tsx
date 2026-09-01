import { type ComponentType, useEffect, useState } from 'react'
import { ArrowLeftRight, BarChart3, Building2, ChevronRight, Library, Users } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import {
  HoustonBadge,
  TerrainCard,
  TerrainSectionLabel,
  TerrainSwitch,
} from '@/components/ui/terrain'
import {
  canAccessManagementSpace,
  canCreateCatalogActionPlanFromBootstrapHints,
  canManageOrganizationFromBootstrapHints,
  canManageRuntimeConfigFromBootstrapHints,
  canViewActionPlanCatalogFromBootstrapHints,
  canViewTeamFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { canSwitchEstablishment } from '@/features/auth/lib/establishment-switch'
import { AccountDeletionCard } from '@/features/auth/pages/account-deletion-card'
import { toRoleEnum } from '@/features/auth/lib/role'
import type { RoleEnum } from '@/features/auth/types'
import { canShowAnalyticsNavigation } from '@/features/navigation/lib/shared-navigation'
import {
  useNotificationPreferencesQuery,
  useUpdateNotificationPreferencesMutation,
} from '@/features/notifications/hooks'
import { GamificationScoreCard } from '@/features/gamification/components/gamification-score-card'
import { useGamificationOverviewQuery } from '@/features/gamification/hooks'
import {
  NativePushPermissionDeniedError,
  checkNativePushReceivePermission,
  optInNativePush,
} from '@/lib/native-push-session'
import { getAppRuntime } from '@/lib/runtime'
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
  const {
    activeMembership,
    bootstrap,
    isBootstrapping,
    isReady,
    memberships,
    user,
  } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)

  const firstName = readOptionalUserName(user, 'first_name')
  const lastName = readOptionalUserName(user, 'last_name')
  const identityLabel = user ? (user.email ?? user.username) : null
  const role = toRoleEnum(activeMembership?.role)
  const canAccessManagement = canAccessManagementSpace(permissionHints)
  const canViewTeam = canViewTeamFromBootstrapHints(permissionHints)
  const canManageOrganization = canManageOrganizationFromBootstrapHints(permissionHints)
  const canManageRuntimeConfig = canManageRuntimeConfigFromBootstrapHints(permissionHints)
  const canShowActionPlansNav =
    canViewActionPlanCatalogFromBootstrapHints(permissionHints) ||
    canCreateCatalogActionPlanFromBootstrapHints(permissionHints)
  const canShowStaffActionPlansNav = canShowActionPlansNav && !canAccessManagement
  const canShowAnalyticsNav = canShowAnalyticsNavigation(bootstrap)
  const displayName = buildDisplayName(firstName, lastName, identityLabel)
  const initials = buildInitials(firstName, lastName, identityLabel)
  const roleEstablishmentLine = buildRoleEstablishmentLine(
    role,
    activeMembership?.establishment_name,
  )
  const establishmentId = activeMembership?.establishment_id ?? null
  const showSwitchEstablishment = canSwitchEstablishment(memberships, establishmentId)
  const showEstablishmentAdmin =
    Boolean(establishmentId) &&
    (canManageOrganization || role === 'owner' || role === 'director' || canManageRuntimeConfig)
  const notificationPreferencesQuery = useNotificationPreferencesQuery(establishmentId)
  const gamificationOverviewQuery = useGamificationOverviewQuery(establishmentId)
  const updateNotificationPreferencesMutation =
    useUpdateNotificationPreferencesMutation(establishmentId)
  const notificationsEnabled = notificationPreferencesQuery.data?.notifications_enabled ?? true
  const pushEnabled = notificationPreferencesQuery.data?.push_enabled ?? false
  const isNativeRuntime = getAppRuntime() === 'native'
  const [pushOptInError, setPushOptInError] = useState<string | null>(null)
  const [isPushOptingIn, setIsPushOptingIn] = useState(false)
  const [osReceive, setOsReceive] = useState<'granted' | 'denied' | 'prompt' | 'unavailable'>(
    'unavailable',
  )
  const isNotificationTogglePending =
    notificationPreferencesQuery.isLoading || updateNotificationPreferencesMutation.isPending

  useEffect(() => {
    if (!isNativeRuntime) {
      return
    }
    let cancelled = false
    void checkNativePushReceivePermission().then((receive) => {
      if (!cancelled) {
        setOsReceive(receive)
      }
    })
    return () => {
      cancelled = true
    }
  }, [isNativeRuntime, pushEnabled])

  if (!isReady || isBootstrapping) {
    return (
      <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement du profil...</p>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-3 pb-4 pt-3">
      <GamificationScoreCard
        establishmentId={establishmentId}
        data={gamificationOverviewQuery.data}
        isLoading={gamificationOverviewQuery.isLoading}
        isError={gamificationOverviewQuery.isError}
        onRetry={() => {
          void gamificationOverviewQuery.refetch()
        }}
      />

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
        {showSwitchEstablishment ? (
          <ProfileManagementNavCard
            icon={ArrowLeftRight}
            iconClassName="bg-[#F3F0FF] text-[#6B4FD8]"
            title="Changer d'établissement"
            subtitle={
              activeMembership?.establishment_name
                ? `Actuellement : ${activeMembership.establishment_name}`
                : 'Basculer entre vos sites actifs'
            }
            onClick={() => onNavigate?.('/general/switch-establishment')}
          />
        ) : null}
        <TerrainCard className="divide-y divide-[#E8E6DF] p-0">
          <TerrainSwitch
            label="Notifications"
            checked={notificationsEnabled}
            disabled={isNotificationTogglePending}
            onCheckedChange={(checked) => {
              updateNotificationPreferencesMutation.mutate({
                notifications_enabled: checked,
              })
            }}
          />
          {notificationPreferencesQuery.isError ? (
            <p className="px-4 pb-3.5 text-xs text-[#E24B4A]">
              Les préférences de notifications n&apos;ont pas pu être chargées.
            </p>
          ) : null}
          {updateNotificationPreferencesMutation.isError ? (
            <p className="px-4 pb-3.5 text-xs text-[#E24B4A]">
              La mise à jour des notifications a échoué.
            </p>
          ) : null}
          {isNativeRuntime ? (
            <>
              <TerrainSwitch
                label="Notifications push"
                checked={pushEnabled}
                disabled={
                  isNotificationTogglePending ||
                  isPushOptingIn ||
                  !notificationsEnabled
                }
                onCheckedChange={(checked) => {
                  setPushOptInError(null)
                  if (!checked) {
                    updateNotificationPreferencesMutation.mutate({ push_enabled: false })
                    return
                  }
                  setIsPushOptingIn(true)
                  void optInNativePush()
                    .then(() => {
                      updateNotificationPreferencesMutation.mutate({ push_enabled: true })
                    })
                    .catch((error: unknown) => {
                      if (error instanceof NativePushPermissionDeniedError) {
                        setPushOptInError(
                          "Les notifications système n'ont pas été autorisées.",
                        )
                        return
                      }
                      setPushOptInError("L'activation des notifications push a échoué.")
                    })
                    .finally(() => {
                      setIsPushOptingIn(false)
                    })
                }}
              />
              {pushEnabled && osReceive === 'denied' ? (
                <p className="px-4 pb-3.5 text-xs text-[#E24B4A]">
                  Les notifications sont bloquées dans les réglages du téléphone.
                </p>
              ) : null}
              {pushOptInError ? (
                <p className="px-4 pb-3.5 text-xs text-[#E24B4A]">{pushOptInError}</p>
              ) : null}
            </>
          ) : null}
        </TerrainCard>
      </div>

      {canShowAnalyticsNav ? (
        <div className="space-y-2">
          <TerrainSectionLabel>Analyse</TerrainSectionLabel>
          <ProfileManagementNavCard
            icon={BarChart3}
            iconClassName="bg-[#E8F7F0] text-[#114660]"
            title="Analyse"
            subtitle="Indicateurs opérationnels"
            onClick={() => onNavigate?.('/analytics')}
          />
        </div>
      ) : null}

      {canManageOrganization || showEstablishmentAdmin ? (
        <div className="space-y-2">
          <TerrainSectionLabel dotVariant="primary" className="py-0">
            Administration
          </TerrainSectionLabel>
          {canManageOrganization ? (
            <ProfileManagementNavCard
              icon={Building2}
              iconClassName="bg-[#EEF2FF] text-[#1B4FD8]"
              title="Gestion de l'organisation"
              subtitle="Établissements, membres et propriétaires"
              onClick={() => onNavigate?.('/organization')}
            />
          ) : null}
          {showEstablishmentAdmin && establishmentId ? (
            <ProfileManagementNavCard
              icon={Building2}
              iconClassName="bg-[#F3F0FF] text-[#6B4FD8]"
              title="Gestion de l'établissement"
              subtitle="Vue d'ensemble et membres de l'établissement actif"
              onClick={() => onNavigate?.(`/organization/establishments/${establishmentId}`)}
            />
          ) : null}
        </div>
      ) : null}

      {canViewTeam && !canAccessManagement ? (
        <ProfileManagementNavCard
          icon={Users}
          iconClassName="bg-[#E8F7F0] text-[#1D9E75]"
          title="Équipe"
          subtitle="Voir l'équipe"
          onClick={() => onNavigate?.('/team')}
        />
      ) : null}

      {canShowStaffActionPlansNav ? (
        <ProfileManagementNavCard
          icon={Library}
          iconClassName="bg-[#EEF2FF] text-[#1B4FD8]"
          title="Bibliothèque"
          subtitle="Plans d’action réutilisables"
          onClick={() => onNavigate?.('/action-plans')}
        />
      ) : null}

      {canAccessManagement ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2 px-0.5">
            <TerrainSectionLabel dotVariant="primary" className="py-0">
              Opérations
            </TerrainSectionLabel>
            {role ? (
              <HoustonBadge variant="blue">{formatRoleDisplay(role).toUpperCase()}</HoustonBadge>
            ) : null}
          </div>

          <div className="space-y-2">
            {canShowActionPlansNav ? (
              <ProfileManagementNavCard
                icon={Library}
                iconClassName="bg-[#EEF2FF] text-[#1B4FD8]"
                title="Bibliothèque"
                subtitle="Plans d’action réutilisables"
                onClick={() => onNavigate?.('/action-plans')}
              />
            ) : null}

            <ProfileManagementNavCard
              icon={Users}
              iconClassName="bg-[#E8F7F0] text-[#1D9E75]"
              title="Équipe"
              subtitle="Gérer les membres et autorisations"
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

      <AccountDeletionCard
        disabled={isLoggingOut}
        onDeleted={async () => {
          await onSignOut?.()
        }}
      />
    </div>
  )
}
