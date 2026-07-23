import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import type { EstablishmentAdminOverview } from '../types'
import { formatOrgRole } from './organization-establishments-tab'

type EstablishmentAdminOverviewTabProps = {
  overview: EstablishmentAdminOverview
}

function MetricTile({ label, value }: { label: string; value: string | number }) {
  return (
    <TerrainCard className="space-y-1 p-4">
      <p className={cn('text-xs font-medium uppercase tracking-wide', terrain.muted)}>{label}</p>
      <p className="text-2xl font-semibold tabular-nums text-[#1a1a1a]">{value}</p>
    </TerrainCard>
  )
}

export function EstablishmentAdminOverviewTab({ overview }: EstablishmentAdminOverviewTabProps) {
  const { metrics, operational_config: config } = overview
  const configLabel =
    config.status === 'configured' ? 'Configuration à jour' : 'Configuration à compléter'

  return (
    <div className="space-y-5">
      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-[#1a1a1a]">Indicateurs</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <MetricTile label="Signaux en attente" value={metrics.signals_open} />
          <MetricTile label="Signaux en cours" value={metrics.signals_in_progress} />
          <MetricTile label="Plans d’action en cours" value={metrics.action_plans_in_progress} />
          <MetricTile label="Plans d’action planifiés" value={metrics.action_plans_scheduled} />
          <MetricTile
            label="Moy. observations / semaine"
            value={metrics.observations_weekly_average.toFixed(1)}
          />
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-[#1a1a1a]">Configuration opérationnelle</h3>
        <TerrainCard className="space-y-2 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <HoustonBadge variant={config.status === 'configured' ? 'green' : 'blue'}>
              {configLabel}
            </HoustonBadge>
          </div>
          <p className={cn('text-sm', terrain.muted)}>
            {config.active_business_unit_count} pôles actifs ·{' '}
            {config.active_activity_subject_count} sujets actifs
            {config.active_business_units_without_subjects_count > 0
              ? ` · ${config.active_business_units_without_subjects_count} pôle(s) sans sujet`
              : ''}
          </p>
        </TerrainCard>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-[#1a1a1a]">Direction</h3>
        {overview.directors.length === 0 ? (
          <p className={cn('text-sm', terrain.muted)}>Aucun director.</p>
        ) : (
          overview.directors.map((director) => (
            <TerrainCard key={director.membership_id} className="space-y-1 p-4">
              <p className="text-sm font-semibold text-[#1a1a1a]">{director.display_name}</p>
              <p className={cn('text-xs', terrain.muted)}>{director.email}</p>
              <HoustonBadge variant={director.status === 'active' ? 'green' : 'blue'}>
                {formatOrgRole('director')} · {director.status}
              </HoustonBadge>
            </TerrainCard>
          ))
        )}
      </section>

      <p className={cn('text-sm', terrain.muted)}>
        {overview.active_member_count} membres actifs · {overview.business_unit_count} pôles
      </p>
    </div>
  )
}
