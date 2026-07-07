import { cn } from '@/lib/utils'

import type { ActionPlanPoleTaskSummary } from '../lib/action-plan-display'

type ActionPlanExecutionTaskFiltersProps = {
  poles: Pick<ActionPlanPoleTaskSummary, 'businessUnitId' | 'label'>[]
  selectedPoleId: string | null
  onSelectedPoleIdChange: (poleId: string | null) => void
}

function filterButtonClass(isSelected: boolean): string {
  return cn(
    'rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
    isSelected
      ? 'bg-[#EEF2FF] text-[#1B4FD8]'
      : 'bg-[#F5F4F0] text-[#555] hover:bg-[#EBEAE4]',
  )
}

export function ActionPlanExecutionTaskFilters({
  poles,
  selectedPoleId,
  onSelectedPoleIdChange,
}: ActionPlanExecutionTaskFiltersProps) {
  return (
    <div
      role="group"
      aria-label="Filtrer les tâches par pôle"
      className="flex flex-wrap gap-2"
    >
      <button
        type="button"
        className={filterButtonClass(selectedPoleId === null)}
        aria-pressed={selectedPoleId === null}
        onClick={() => onSelectedPoleIdChange(null)}
      >
        Tous
      </button>
      {poles.map((pole) => (
        <button
          key={pole.businessUnitId}
          type="button"
          className={filterButtonClass(selectedPoleId === pole.businessUnitId)}
          aria-pressed={selectedPoleId === pole.businessUnitId}
          onClick={() => onSelectedPoleIdChange(pole.businessUnitId)}
        >
          {pole.label}
        </button>
      ))}
    </div>
  )
}
