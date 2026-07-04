import { TerrainCard } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'

import { truncateActionPlanDescription } from '../lib/action-plan-display'
import { canShowActionPlanUse } from '../lib/action-plan-permission-hints'
import type { ActionPlanListItem } from '../types'

type ActionPlanCatalogCardProps = {
  item: ActionPlanListItem
  onOpen: (actionPlanId: string) => void
  onUse: (actionPlanId: string) => void
}

export function ActionPlanCatalogCard({ item, onOpen, onUse }: ActionPlanCatalogCardProps) {
  const showUse = canShowActionPlanUse(item.permission_hints)
  const showInvolvedPoles = item.involved_pole_count > 1

  return (
    <TerrainCard className="space-y-2 p-3">
      <button type="button" className="w-full text-left" onClick={() => onOpen(item.id)}>
        <p className="text-sm font-semibold text-[#1a1a1a]">{item.title}</p>
        {item.description ? (
          <p className="mt-1 text-xs text-[#7D7B75]">
            {truncateActionPlanDescription(item.description)}
          </p>
        ) : null}
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-[#7D7B75]">
          <span>{item.pilot_business_unit.label}</span>
          <span>{item.task_count} tâche{item.task_count > 1 ? 's' : ''}</span>
          {showInvolvedPoles ? <span>{item.involved_pole_count} pôles</span> : null}
        </div>
      </button>
      {showUse ? (
        <Button
          type="button"
          size="sm"
          className="h-9 w-full rounded-xl"
          onClick={() => onUse(item.id)}
        >
          Utiliser
        </Button>
      ) : null}
    </TerrainCard>
  )
}
