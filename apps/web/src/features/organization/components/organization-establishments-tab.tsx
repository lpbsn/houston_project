import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { formatMembershipRoleDisplay } from '@/lib/display-names'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { canResumeDraftOnboarding } from '../lib/can-resume-draft-onboarding'
import type { OrganizationAdminEstablishment } from '../types'

type OrganizationEstablishmentsTabProps = {
  establishments: OrganizationAdminEstablishment[]
  canCreate: boolean
  onManage: (establishmentId: string) => void
  onResume: (establishmentId: string, sessionId: string) => void
  onCreate: () => void
}

function directorsLabel(establishment: OrganizationAdminEstablishment): string {
  if (establishment.directors.length === 0) {
    return 'Aucun director'
  }
  return establishment.directors
    .map((director) => `${director.display_name} (${director.status})`)
    .join(', ')
}

export function OrganizationEstablishmentsTab({
  establishments,
  canCreate,
  onManage,
  onResume,
  onCreate,
}: OrganizationEstablishmentsTabProps) {
  const active = establishments.filter((row) => row.status === 'active')
  const drafts = establishments.filter((row) => row.status === 'draft')

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-[#1a1a1a]">Établissements</h2>
        {canCreate ? (
          <Button type="button" onClick={onCreate}>
            Ajouter un établissement
          </Button>
        ) : null}
      </div>

      <section className="space-y-3">
        <h3 className={cn('text-sm font-semibold', terrain.muted)}>Actifs</h3>
        {active.length === 0 ? (
          <p className={cn('text-sm', terrain.muted)}>Aucun établissement actif.</p>
        ) : (
          active.map((establishment) => (
            <TerrainCard key={establishment.id} className="space-y-3 p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-[#1a1a1a]">{establishment.name}</p>
                  <p className={cn('mt-1 text-xs', terrain.muted)}>
                    {directorsLabel(establishment)}
                  </p>
                  <p className={cn('mt-1 text-xs', terrain.muted)}>
                    {establishment.active_member_count} membres actifs ·{' '}
                    {establishment.business_unit_count} pôles
                  </p>
                </div>
                <HoustonBadge variant="green">Actif</HoustonBadge>
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => onManage(establishment.id)}
              >
                Gérer l&apos;établissement
              </Button>
            </TerrainCard>
          ))
        )}
      </section>

      <section className="space-y-3">
        <h3 className={cn('text-sm font-semibold', terrain.muted)}>En configuration</h3>
        {drafts.length === 0 ? (
          <p className={cn('text-sm', terrain.muted)}>Aucun établissement en configuration.</p>
        ) : (
          drafts.map((establishment) => {
            const canResume = canResumeDraftOnboarding(establishment)
            return (
              <TerrainCard key={establishment.id} className="space-y-3 p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-[#1a1a1a]">{establishment.name}</p>
                    <p className={cn('mt-1 text-xs', terrain.muted)}>
                      {directorsLabel(establishment)}
                    </p>
                    {establishment.onboarding_current_step ? (
                      <p className={cn('mt-1 text-xs', terrain.muted)}>
                        Étape : {establishment.onboarding_current_step}
                      </p>
                    ) : null}
                  </div>
                  <HoustonBadge variant="gray">En configuration</HoustonBadge>
                </div>
                {canResume ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() =>
                      onResume(establishment.id, establishment.onboarding_session_id!)
                    }
                  >
                    Reprendre la configuration
                  </Button>
                ) : null}
              </TerrainCard>
            )
          })
        )}
      </section>
    </div>
  )
}

export function formatOrgRole(role: string): string {
  return formatMembershipRoleDisplay(role)
}
