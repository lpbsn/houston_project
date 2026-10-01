import { Input } from '@/components/ui/input'
import { TerrainFilterChip } from '@/components/ui/terrain'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { useLgViewport } from '@/lib/lg-viewport'
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
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const businessUnitQuery = useBusinessUnitTreeQuery(establishmentId, { staleTime: 60_000 })
  const businessUnits = (businessUnitQuery.data?.business_units ?? []).map((unit) => ({
    id: unit.id,
    label: unit.specific_name,
  }))

  function renderChip(label: string, pressed: boolean, onClick: () => void, shrink = false) {
    if (isDesktopWeb) {
      return (
        <button
          type="button"
          className={cn(filterButtonClass(pressed), shrink && 'shrink-0')}
          onClick={onClick}
        >
          {label}
        </button>
      )
    }
    return (
      <TerrainFilterChip
        pressed={pressed}
        onClick={onClick}
        className={shrink ? 'shrink-0' : undefined}
      >
        {label}
      </TerrainFilterChip>
    )
  }

  return (
    <div className="space-y-3">
      <Input
        value={searchQuery}
        onChange={(event) => onSearchQueryChange(event.target.value)}
        placeholder="Rechercher par titre"
        aria-label="Rechercher par titre"
        className="h-9 rounded-full border-[#E8E6DF] bg-[#F5F4F0] shadow-sm"
      />
      <div
        data-testid="action-plan-hub-pole-filters"
        className={cn(
          'flex gap-2 overflow-x-auto',
          isDesktopWeb && 'lg:flex-wrap lg:overflow-visible',
        )}
      >
        {renderChip('Tous les pôles', !businessUnitId, () => onBusinessUnitIdChange(''), true)}
        {businessUnits.map((unit) => (
          <span key={unit.id} className="contents">
            {renderChip(
              unit.label,
              businessUnitId === unit.id,
              () => onBusinessUnitIdChange(unit.id),
              true,
            )}
          </span>
        ))}
      </div>
      {renderChip('Créés par moi', createdByMe, () => onCreatedByMeChange(!createdByMe))}
    </div>
  )
}
