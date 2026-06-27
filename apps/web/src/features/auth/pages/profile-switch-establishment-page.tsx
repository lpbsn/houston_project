import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Building2, LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { switchEstablishment } from '@/features/auth/api'
import { toRoleEnum } from '@/features/auth/lib/role'
import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'
import { toErrorMessage } from '@/lib/error-message'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ProfileSwitchEstablishmentPageProps = {
  onNavigate: (path: string, options?: { replace?: boolean }) => void
}

const ROLE_DISPLAY_LABELS = {
  owner: 'Propriétaire',
  director: 'Directeur',
  manager: 'Manager',
  staff: 'Équipe',
} as const

export function ProfileSwitchEstablishmentPage({
  onNavigate,
}: ProfileSwitchEstablishmentPageProps) {
  const { activeMembership, isBootstrapping, isReady, memberships } = useAuth()
  const [pendingEstablishmentId, setPendingEstablishmentId] = useState<string | null>(null)
  const [selectorError, setSelectorError] = useState<string | null>(null)
  const activeEstablishmentId = activeMembership?.establishment_id ?? null

  const switchMutation = useMutation({
    mutationFn: switchEstablishment,
  })

  async function handleSelectEstablishment(establishmentId: string) {
    if (establishmentId === activeEstablishmentId) {
      return
    }

    setSelectorError(null)
    setPendingEstablishmentId(establishmentId)

    try {
      await switchMutation.mutateAsync({ establishment_id: establishmentId })
      onNavigate('/reporting', { replace: true })
    } catch (error) {
      setSelectorError(
        toErrorMessage(error, 'Impossible de sélectionner cet établissement.'),
      )
    } finally {
      setPendingEstablishmentId(null)
    }
  }

  if (!isReady || isBootstrapping) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement...</p>
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-3 pb-4 pt-3">
      <p className={cn('px-0.5 text-sm', terrain.muted)}>
        Sélectionnez l&apos;établissement avec lequel vous souhaitez travailler.
      </p>

      <div className="space-y-2">
        {memberships.map((membership) => {
          const isActive = membership.establishment_id === activeEstablishmentId
          const isPending = pendingEstablishmentId === membership.establishment_id
          const role = toRoleEnum(membership.role)
          const roleLabel = role ? ROLE_DISPLAY_LABELS[role] : membership.role

          return (
            <button
              key={membership.id}
              type="button"
              className={cn(
                'w-full text-left active:opacity-90',
                isActive && 'cursor-default',
              )}
              disabled={isActive || isPending}
              onClick={() => {
                void handleSelectEstablishment(membership.establishment_id)
              }}
            >
              <TerrainCard
                className={cn(
                  'flex min-h-11 items-center gap-3 p-4',
                  isActive && 'border-[#1D9E75]/30 bg-[#F7FCFA]',
                )}
              >
                <span
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#EEF2FF] text-[#1B4FD8]"
                  aria-hidden
                >
                  <Building2 className="h-5 w-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-[#1a1a1a]">
                    {membership.establishment_name}
                  </span>
                  <span className={cn('mt-0.5 block truncate text-xs', terrain.muted)}>
                    {membership.organization_name} · {roleLabel}
                  </span>
                </span>
                {isPending ? (
                  <LoaderCircle className="h-4 w-4 shrink-0 animate-spin text-[#1B4FD8]" aria-hidden />
                ) : isActive ? (
                  <HoustonBadge variant="green">Actif</HoustonBadge>
                ) : null}
              </TerrainCard>
            </button>
          )
        })}
      </div>

      {selectorError ? (
        <p className="px-0.5 text-xs text-[#E24B4A]">{selectorError}</p>
      ) : null}
    </div>
  )
}
