import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'

import type { ActionPlanExecutionDetail } from '../types'

type ActionPlanExecutionDetailDescriptionSectionProps = {
  execution: ActionPlanExecutionDetail
}

export function ActionPlanExecutionDetailDescriptionSection({
  execution,
}: ActionPlanExecutionDetailDescriptionSectionProps) {
  const description = execution.description.trim()
  if (!description) {
    return null
  }

  return (
    <section className="flex flex-col gap-1.5">
      <TerrainSectionLabel>Description</TerrainSectionLabel>
      <TerrainCard>
        <p className="whitespace-pre-wrap text-sm text-[#222222]">{description}</p>
      </TerrainCard>
    </section>
  )
}
