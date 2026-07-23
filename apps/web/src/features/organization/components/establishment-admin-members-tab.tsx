import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import type {
  EstablishmentAdminMemberFilterOptions,
  EstablishmentAdminMemberListFilters,
  EstablishmentAdminMembership,
} from '../types'
import { formatOrgRole } from './organization-establishments-tab'

type EstablishmentAdminMembersTabProps = {
  members: EstablishmentAdminMembership[]
  filterOptions: EstablishmentAdminMemberFilterOptions | undefined
  filters: EstablishmentAdminMemberListFilters
  onFiltersChange: (next: EstablishmentAdminMemberListFilters) => void
  onInvite: () => void
  canInvite: boolean
  onDeactivate: (membershipId: string) => void
  onActivate: (membershipId: string) => void
  onEdit: (member: EstablishmentAdminMembership) => void
  pendingMembershipId: string | null
  isLoading: boolean
  actionError: string | null
}

function statusBadgeVariant(status: string): 'green' | 'blue' | 'gray' {
  if (status === 'active') return 'green'
  if (status === 'invited') return 'blue'
  return 'gray'
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      dateStyle: 'medium',
    }).format(new Date(value))
  } catch {
    return '—'
  }
}

export function EstablishmentAdminMembersTab({
  members,
  filterOptions,
  filters,
  onFiltersChange,
  onInvite,
  canInvite,
  onDeactivate,
  onActivate,
  onEdit,
  pendingMembershipId,
  isLoading,
  actionError,
}: EstablishmentAdminMembersTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-[#1a1a1a]">Membres</h3>
        {canInvite ? (
          <Button type="button" onClick={onInvite}>
            Inviter
          </Button>
        ) : null}
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
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
          {(filterOptions?.business_units ?? []).map((row) => (
            <option key={row.id} value={row.id}>
              {row.label}
            </option>
          ))}
        </select>
      </div>

      {actionError ? <p className="text-sm text-red-600">{actionError}</p> : null}

      {isLoading ? (
        <p className={cn('text-sm', terrain.muted)}>Chargement des membres…</p>
      ) : members.length === 0 ? (
        <p className={cn('text-sm', terrain.muted)}>Aucun membre trouvé.</p>
      ) : (
        members.map((member) => {
          const displayName =
            [member.first_name, member.last_name].filter(Boolean).join(' ').trim() ||
            member.email
          const dateLabel =
            member.status === 'invited'
              ? `Invité le ${formatDate(member.invited_at)}`
              : `Activé le ${formatDate(member.activated_at)}`
          const poles =
            member.business_units.length === 0
              ? '—'
              : member.business_units.map((unit) => unit.label).join(', ')

          return (
            <TerrainCard key={member.id} className="space-y-3 p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-[#1a1a1a]">{displayName}</p>
                  <p className={cn('text-xs', terrain.muted)}>{member.email}</p>
                </div>
                <HoustonBadge variant={statusBadgeVariant(member.status)}>
                  {formatOrgRole(member.role)} · {member.status}
                </HoustonBadge>
              </div>
              <p className={cn('text-xs', terrain.muted)}>Pôles : {poles}</p>
              <p className={cn('text-xs', terrain.muted)}>{dateLabel}</p>
              <div className="flex flex-wrap gap-2">
                {member.permission_hints.can_edit_role ||
                member.permission_hints.can_edit_scopes ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={pendingMembershipId === member.id}
                    onClick={() => onEdit(member)}
                  >
                    Modifier
                  </Button>
                ) : null}
                {member.permission_hints.can_edit_status && member.status === 'active' ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={pendingMembershipId === member.id}
                    onClick={() => onDeactivate(member.id)}
                  >
                    Désactiver
                  </Button>
                ) : null}
                {member.permission_hints.can_edit_status &&
                member.status === 'deactivated' ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={pendingMembershipId === member.id}
                    onClick={() => onActivate(member.id)}
                  >
                    Réactiver
                  </Button>
                ) : null}
              </div>
            </TerrainCard>
          )
        })
      )}
    </div>
  )
}
