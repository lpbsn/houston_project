import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import type {
  OrganizationAdminMember,
  OrganizationAdminMemberFilterOptions,
  OrganizationMemberListFilters,
} from '../types'
import { formatOrgRole } from './organization-establishments-tab'

type OrganizationMembersTabProps = {
  members: OrganizationAdminMember[]
  filterOptions: OrganizationAdminMemberFilterOptions | undefined
  filters: OrganizationMemberListFilters
  onFiltersChange: (next: OrganizationMemberListFilters) => void
  onOpenEstablishment: (establishmentId: string) => void
  isLoading: boolean
}

function statusBadgeVariant(status: string): 'green' | 'blue' | 'gray' {
  if (status === 'active') return 'green'
  if (status === 'invited') return 'blue'
  return 'gray'
}

export function OrganizationMembersTab({
  members,
  filterOptions,
  filters,
  onFiltersChange,
  onOpenEstablishment,
  isLoading,
}: OrganizationMembersTabProps) {
  const businessUnits = (filterOptions?.business_units ?? []).filter((unit) =>
    filters.establishment_id
      ? unit.establishment_id === filters.establishment_id
      : true,
  )

  return (
    <div className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <Input
          value={filters.q ?? ''}
          onChange={(event) =>
            onFiltersChange({ ...filters, q: event.target.value || undefined })
          }
          placeholder="Rechercher nom ou email"
          aria-label="Recherche membres"
        />
        <select
          className="min-h-11 rounded-xl border border-[#E8E6E1] bg-white px-3 text-sm"
          value={filters.establishment_id ?? ''}
          onChange={(event) =>
            onFiltersChange({
              ...filters,
              establishment_id: event.target.value || undefined,
              business_unit_id: undefined,
            })
          }
          aria-label="Filtrer par établissement"
        >
          <option value="">Tous les établissements</option>
          {(filterOptions?.establishments ?? []).map((row) => (
            <option key={row.id} value={row.id}>
              {row.name}
            </option>
          ))}
        </select>
        <select
          className="min-h-11 rounded-xl border border-[#E8E6E1] bg-white px-3 text-sm"
          value={filters.business_unit_id ?? ''}
          onChange={(event) =>
            onFiltersChange({
              ...filters,
              business_unit_id: event.target.value || undefined,
            })
          }
          aria-label="Filtrer par pôle"
        >
          <option value="">Tous les pôles</option>
          {businessUnits.map((row) => (
            <option key={row.id} value={row.id}>
              {row.label}
            </option>
          ))}
        </select>
        <select
          className="min-h-11 rounded-xl border border-[#E8E6E1] bg-white px-3 text-sm"
          value={filters.role ?? ''}
          onChange={(event) =>
            onFiltersChange({ ...filters, role: event.target.value || undefined })
          }
          aria-label="Filtrer par rôle"
        >
          <option value="">Tous les rôles</option>
          {(filterOptions?.roles ?? []).map((role) => (
            <option key={role} value={role}>
              {formatOrgRole(role)}
            </option>
          ))}
        </select>
        <select
          className="min-h-11 rounded-xl border border-[#E8E6E1] bg-white px-3 text-sm"
          value={filters.status ?? ''}
          onChange={(event) =>
            onFiltersChange({ ...filters, status: event.target.value || undefined })
          }
          aria-label="Filtrer par statut"
        >
          <option value="">Tous les statuts</option>
          {(filterOptions?.statuses ?? []).map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <p className={cn('text-sm', terrain.muted)}>Chargement des membres…</p>
      ) : members.length === 0 ? (
        <p className={cn('text-sm', terrain.muted)}>Aucun membre trouvé.</p>
      ) : (
        members.map((member) => {
          const displayName =
            [member.first_name, member.last_name].filter(Boolean).join(' ').trim() ||
            member.email
          return (
            <TerrainCard key={member.user_id} className="space-y-3 p-4">
              <div>
                <p className="text-sm font-semibold text-[#1a1a1a]">{displayName}</p>
                <p className={cn('text-xs', terrain.muted)}>{member.email}</p>
              </div>
              <ul className="space-y-2">
                {member.memberships.map((membership) => (
                  <li
                    key={membership.membership_id}
                    className="rounded-xl border border-[#EFEDE8] bg-[#FAFAF8] p-3"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        className="text-sm font-medium text-[#1B4FD8] underline-offset-2 hover:underline"
                        onClick={() => onOpenEstablishment(membership.establishment_id)}
                      >
                        {membership.establishment_name}
                      </button>
                      <HoustonBadge variant="blue">{formatOrgRole(membership.role)}</HoustonBadge>
                      <HoustonBadge variant={statusBadgeVariant(membership.status)}>
                        {membership.status}
                      </HoustonBadge>
                    </div>
                    {membership.business_units.length > 0 ? (
                      <p className={cn('mt-1 text-xs', terrain.muted)}>
                        Pôles :{' '}
                        {membership.business_units.map((unit) => unit.label).join(', ')}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </TerrainCard>
          )
        })
      )}

      {filters.q ||
      filters.establishment_id ||
      filters.business_unit_id ||
      filters.role ||
      filters.status ? (
        <Button type="button" variant="ghost" onClick={() => onFiltersChange({})}>
          Réinitialiser les filtres
        </Button>
      ) : null}
    </div>
  )
}
