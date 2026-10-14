import { BusinessUnitBadge } from '@/components/ui/terrain/business-unit-badge'
import type { ActionPlanExecutionFeedItem } from '../types'

type Props = Pick<ActionPlanExecutionFeedItem, 'pilot_business_unit' | 'involved_poles'>

export function ActionPlanPoleBadges({ pilot_business_unit, involved_poles }: Props) {
  const poles = new Map<string, { id: string; specific_name: string; color_index?: number | null }>([[pilot_business_unit.id, pilot_business_unit]])
  for (const { business_unit } of involved_poles) {
    if (!business_unit || typeof business_unit !== 'object') continue
    const pole = business_unit as Record<string, unknown>
    if (typeof pole.id !== 'string' || typeof pole.specific_name !== 'string') continue
    if (!poles.has(pole.id)) poles.set(pole.id, {
      id: pole.id,
      specific_name: pole.specific_name,
      color_index: typeof pole.color_index === 'number' ? pole.color_index : null,
    })
  }
  return Array.from(poles.values()).filter((pole) => pole.specific_name.trim()).map((pole) => (
    <BusinessUnitBadge key={pole.id} colorIndex={pole.color_index} className="break-words">
      {pole.specific_name}
    </BusinessUnitBadge>
  ))
}
