import { ChevronRight, Layers2 } from 'lucide-react'

import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { formatCatalogStatusLabel, truncateActionPlanDescription } from '../lib/action-plan-display'
import { canShowActionPlanUse } from '../lib/action-plan-permission-hints'
import type { ActionPlanListItem } from '../types'

type ActionPlanCatalogCardProps = {
  item: ActionPlanListItem
  onOpen: (actionPlanId: string) => void
  onUse: (actionPlanId: string) => void
}

const catalogBadgeClassName =
  'inline-flex h-6 items-center justify-center rounded-full px-2.5 text-xs'

export function ActionPlanCatalogCard({ item, onOpen, onUse }: ActionPlanCatalogCardProps) {
  const showUse = canShowActionPlanUse(item.permission_hints)
  const showInvolvedPoles = item.involved_pole_count > 1
  const isInactive = item.catalog_status === 'inactive'

  return (
    <TerrainCard className="space-y-3 rounded-[20px] p-3.5">
      <button type="button" className="w-full space-y-2 text-left" onClick={() => onOpen(item.id)}>
        <div className="flex items-center gap-2">
          <p className="flex-1 text-sm font-semibold text-[#1a1a1a]">{item.title}</p>
          <ChevronRight className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
        </div>
        {item.description ? (
          <p className="text-xs text-[#7D7B75]">
            {truncateActionPlanDescription(item.description)}
          </p>
        ) : null}
        <div className="flex items-center gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn(catalogBadgeClassName, 'bg-black font-medium text-white')}>
              {item.pilot_business_unit.label}
            </span>
            <span
              className={cn(
                catalogBadgeClassName,
                'gap-1 border border-[#E8E6DF] bg-white text-[#555]',
              )}
            >
              <Layers2 className="h-3.5 w-3.5 shrink-0" aria-hidden />
              {item.task_count} tâche{item.task_count > 1 ? 's' : ''}
            </span>
            {showInvolvedPoles ? (
              <span
                className={cn(
                  catalogBadgeClassName,
                  'border border-[#E8E6DF] bg-white text-[#555]',
                )}
              >
                {item.involved_pole_count} pôles
              </span>
            ) : null}
          </div>
          {isInactive ? (
            <HoustonBadge variant="gray" className="ml-auto shrink-0 text-[10px]">
              {formatCatalogStatusLabel(item.catalog_status)}
            </HoustonBadge>
          ) : null}
        </div>
      </button>
      {showUse ? (
        <Button
          type="button"
          className={cn(
            'h-9 w-full rounded-full text-sm font-semibold text-white',
            terrainBrandAction.bg,
            terrainBrandAction.hover,
          )}
          onClick={() => onUse(item.id)}
        >
          Utiliser ce plan
        </Button>
      ) : null}
    </TerrainCard>
  )
}
