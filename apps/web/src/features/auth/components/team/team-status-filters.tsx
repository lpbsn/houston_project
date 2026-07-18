import { cn } from '@/lib/utils'
import type { TeamMemberStatusCounts, TeamMembershipStatus } from '@/features/auth/lib/team-members'

type TeamStatusFiltersProps = {
  counts: TeamMemberStatusCounts
  selectedStatuses: ReadonlySet<TeamMembershipStatus>
  onSelectTous: () => void
  onToggleStatus: (status: TeamMembershipStatus) => void
}

type FilterOption =
  | { kind: 'tous'; label: string; count: number }
  | { kind: 'status'; status: TeamMembershipStatus; label: string; count: number }

function filterButtonClass(isSelected: boolean): string {
  return cn(
    'flex min-h-11 min-w-0 flex-col items-center justify-center rounded-lg border px-0.5 py-1 text-[10px] font-medium leading-tight transition',
    isSelected
      ? 'border-[#1B4FD8] bg-[#1B4FD8] text-white'
      : 'border-[#E8E6DF] bg-transparent text-[#555]',
  )
}

export function TeamStatusFilters({
  counts,
  selectedStatuses,
  onSelectTous,
  onToggleStatus,
}: TeamStatusFiltersProps) {
  const tousSelected = selectedStatuses.size === 0
  const options: FilterOption[] = [
    { kind: 'tous', label: 'Tous', count: counts.total },
    { kind: 'status', status: 'active', label: 'Actif', count: counts.active },
    { kind: 'status', status: 'deactivated', label: 'Inactif', count: counts.deactivated },
    { kind: 'status', status: 'invited', label: 'Invité', count: counts.invited },
  ]

  return (
    <div role="group" aria-label="Filtrer les membres par statut" className="grid grid-cols-4 gap-1">
      {options.map((option) => {
        if (option.kind === 'tous') {
          return (
            <button
              key="tous"
              type="button"
              className={filterButtonClass(tousSelected)}
              aria-label={`Tous, ${option.count}`}
              aria-pressed={tousSelected}
              onClick={onSelectTous}
            >
              <span className="truncate">{option.label}</span>
              <span className="tabular-nums">{option.count}</span>
            </button>
          )
        }

        const isSelected = selectedStatuses.has(option.status)
        return (
          <button
            key={option.status}
            type="button"
            className={filterButtonClass(isSelected)}
            aria-label={`${option.label}, ${option.count}`}
            aria-pressed={isSelected}
            onClick={() => onToggleStatus(option.status)}
          >
            <span className="truncate">{option.label}</span>
            <span className="tabular-nums">{option.count}</span>
          </button>
        )
      })}
    </div>
  )
}
