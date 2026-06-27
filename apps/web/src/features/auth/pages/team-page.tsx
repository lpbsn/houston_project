import { ChevronRight, UserPlus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainComingSoonState, TerrainErrorState } from '@/components/ui/terrain'
import {
  canAccessManagementSpace,
  canInviteFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TeamPageProps = {
  onNavigate?: (pathname: string) => void
}

export function TeamPage({ onNavigate }: TeamPageProps) {
  const { bootstrap, isBootstrapping, isReady } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const canInvite = canInviteFromBootstrapHints(permissionHints)

  if (!isReady || isBootstrapping) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!canAccessManagementSpace(permissionHints)) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Vous n'avez pas accès à la gestion d'équipe."
        retryLabel="Retour au profil"
        onRetry={() => onNavigate?.('/profile')}
      />
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-3 pb-4 pt-3">
      {canInvite ? (
        <button
          type="button"
          className="w-full text-left active:opacity-90"
          onClick={() => onNavigate?.('/team/invite')}
        >
          <TerrainCard className="flex min-h-11 items-center gap-3 p-4">
            <span
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#EEF2FF] text-[#1B4FD8]"
              aria-hidden
            >
              <UserPlus className="h-5 w-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-[#1a1a1a]">Inviter un membre</span>
              <span className={cn('mt-0.5 block text-xs', terrain.muted)}>
                Créer un lien d&apos;invitation
              </span>
            </span>
            <ChevronRight className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
          </TerrainCard>
        </button>
      ) : null}

      <TerrainComingSoonState
        title="Membres"
        description="La gestion des membres de l'équipe sera disponible prochainement."
      />
    </div>
  )
}
