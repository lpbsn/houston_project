import { useEffect } from 'react'

import { useAuth } from '@/app/auth-provider'
import {
  canManageOrganizationFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { getAuthenticatedLandingPath } from '@/features/auth/lib/authenticated-landing'
import { toRoleEnum } from '@/features/auth/lib/role'
import { Button } from '@/components/ui/button'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type OrganizationEstablishmentPageProps = {
  establishmentId: string
  onNavigate: (path: string, options?: { replace?: boolean }) => void
}

function canAccessOrganizationEstablishmentPage({
  canManageOrganization,
  activeEstablishmentId,
  activeRole,
  establishmentId,
}: {
  canManageOrganization: boolean
  activeEstablishmentId: string | null | undefined
  activeRole: ReturnType<typeof toRoleEnum>
  establishmentId: string
}): boolean {
  if (canManageOrganization) {
    return true
  }

  return activeRole === 'director' && activeEstablishmentId === establishmentId
}

export function OrganizationEstablishmentPage({
  establishmentId,
  onNavigate,
}: OrganizationEstablishmentPageProps) {
  const { activeMembership, bootstrap, isBootstrapping, isReady } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const canManageOrganization = canManageOrganizationFromBootstrapHints(permissionHints)
  const activeEstablishmentId = activeMembership?.establishment_id ?? null
  const activeRole = toRoleEnum(activeMembership?.role)
  const canAccess = canAccessOrganizationEstablishmentPage({
    canManageOrganization,
    activeEstablishmentId,
    activeRole,
    establishmentId,
  })
  const showOperationalConfigCta =
    canAccess && activeEstablishmentId !== null && establishmentId === activeEstablishmentId

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

  if (!isReady || isBootstrapping) {
    return <p className={cn('text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!canAccess) {
    return <p className={cn('text-sm', terrain.muted)}>Redirection...</p>
  }

  return (
    <div className="space-y-4">
      <p className={cn('text-sm', terrain.muted)}>
        Espace de gestion de l&apos;établissement. Contenu détaillé à venir.
      </p>
      <p className="text-sm text-[#1a1a1a]">
        Identifiant : <span className="font-mono text-xs">{establishmentId}</span>
      </p>
      {showOperationalConfigCta ? (
        <Button
          type="button"
          variant="outline"
          onClick={() => onNavigate('/app/operational-config')}
        >
          Configuration opérationnelle
        </Button>
      ) : null}
    </div>
  )
}
