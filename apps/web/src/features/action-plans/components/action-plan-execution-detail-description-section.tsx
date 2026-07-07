import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import type { ActionPlanExecutionDetail } from '../types'

type ActionPlanExecutionDetailDescriptionSectionProps = {
  execution: ActionPlanExecutionDetail
}

export function ActionPlanExecutionDetailDescriptionSection({
  execution,
}: ActionPlanExecutionDetailDescriptionSectionProps) {
  const description = execution.description.trim()

  return (
    <section className="flex flex-col gap-1.5">
      <TerrainSectionLabel>Description</TerrainSectionLabel>
      <TerrainCard>
        {description ? (
          <p className="whitespace-pre-wrap text-sm text-[#555]">{description}</p>
        ) : (
          <p className={cn('text-sm', terrain.muted)}>Aucune description.</p>
        )}
      </TerrainCard>
    </section>
  )
}
