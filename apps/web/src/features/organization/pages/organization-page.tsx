import { useEffect } from 'react'

import { useAuth } from '@/app/auth-provider'
import {
  canManageOrganizationFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { getAuthenticatedLandingPath } from '@/features/auth/lib/authenticated-landing'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type OrganizationPageProps = {
  onNavigate: (path: string, options?: { replace?: boolean }) => void
}

export function OrganizationPage({ onNavigate }: OrganizationPageProps) {
  const { bootstrap, isBootstrapping, isReady } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const canManageOrganization = canManageOrganizationFromBootstrapHints(permissionHints)

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

  return (
    <div className="space-y-3">
      <p className={cn('text-sm', terrain.muted)}>
        Espace de gestion de l&apos;organisation. Le contenu détaillé arrivera dans un prochain lot.
      </p>
    </div>
  )
}
