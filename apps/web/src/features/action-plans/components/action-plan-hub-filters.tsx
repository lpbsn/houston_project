import { Input } from '@/components/ui/input'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { cn } from '@/lib/utils'

type ActionPlanHubFiltersProps = {
  establishmentId: string
  searchQuery: string
  businessUnitId: string
  createdByMe: boolean
  onSearchQueryChange: (value: string) => void
  onBusinessUnitIdChange: (value: string) => void
  onCreatedByMeChange: (value: boolean) => void
}

function filterButtonClass(isSelected: boolean): string {
  return cn(
    'rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
    isSelected
      ? 'bg-[#EEF2FF] text-[#1B4FD8]'
      : 'bg-[#F5F4F0] text-[#555] hover:bg-[#EBEAE4]',
  )
}

export function ActionPlanHubFilters({
  establishmentId,
  searchQuery,
  businessUnitId,
  createdByMe,
  onSearchQueryChange,
  onBusinessUnitIdChange,
  onCreatedByMeChange,
}: ActionPlanHubFiltersProps) {
  const businessUnitQuery = useBusinessUnitTreeQuery(establishmentId, { staleTime: 60_000 })
  const businessUnits = businessUnitQuery.data?.business_units ?? []

  return (
    <div className="space-y-3">
      <Input
        value={searchQuery}
        onChange={(event) => onSearchQueryChange(event.target.value)}
        placeholder="Rechercher par titre"
        aria-label="Rechercher par titre"
        className="h-10 border-[#E8E6DF]"
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={filterButtonClass(!businessUnitId)}
          onClick={() => onBusinessUnitIdChange('')}
        >
          Tous les pôles
        </button>
        {businessUnits.map((unit) => (
          <button
            key={unit.id}
            type="button"
            className={filterButtonClass(businessUnitId === unit.id)}
            onClick={() => onBusinessUnitIdChange(unit.id)}
          >
            {unit.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        className={filterButtonClass(createdByMe)}
        onClick={() => onCreatedByMeChange(!createdByMe)}
      >
        Créés par moi
      </button>
    </div>
  )
}
