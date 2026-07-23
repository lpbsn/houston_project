import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import type { OrganizationAdminOwner } from '../types'

type OrganizationOwnersTabProps = {
  owners: OrganizationAdminOwner[]
  isLoading: boolean
  onInvite: () => void
  onResend: (owner: OrganizationAdminOwner) => void
  isResendingUserId: string | null
}

function statusBadgeVariant(status: string): 'green' | 'blue' | 'gray' {
  if (status === 'active') return 'green'
  if (status === 'invited') return 'blue'
  return 'gray'
}

export function OrganizationOwnersTab({
  owners,
  isLoading,
  onInvite,
  onResend,
  isResendingUserId,
}: OrganizationOwnersTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-[#1a1a1a]">Propriétaires</h2>
        <Button type="button" onClick={onInvite}>
          Inviter un propriétaire
        </Button>
      </div>

      {isLoading ? (
        <p className={cn('text-sm', terrain.muted)}>Chargement…</p>
      ) : owners.length === 0 ? (
        <p className={cn('text-sm', terrain.muted)}>Aucun propriétaire.</p>
      ) : (
        owners.map((owner) => {
          const displayName =
            [owner.first_name, owner.last_name].filter(Boolean).join(' ').trim() ||
            owner.email
          return (
            <TerrainCard key={owner.user_id} className="space-y-3 p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-[#1a1a1a]">{displayName}</p>
                  <p className={cn('text-xs', terrain.muted)}>{owner.email}</p>
                  {owner.invited_at ? (
                    <p className={cn('mt-1 text-xs', terrain.muted)}>
                      Invité le {new Date(owner.invited_at).toLocaleDateString('fr-FR')}
                    </p>
                  ) : null}
                </div>
                <HoustonBadge variant={statusBadgeVariant(owner.status)}>
                  {owner.status}
                </HoustonBadge>
              </div>
              {owner.can_resend_invitation ? (
                <Button
                  type="button"
                  variant="outline"
                  disabled={isResendingUserId === owner.user_id}
                  onClick={() => onResend(owner)}
                >
                  Renvoyer l&apos;invitation
                </Button>
              ) : null}
            </TerrainCard>
          )
        })
      )}
    </div>
  )
}
