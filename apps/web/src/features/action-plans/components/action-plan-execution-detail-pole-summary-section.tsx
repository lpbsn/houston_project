import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'

import { buildActionPlanPoleTaskSummaries } from '../lib/action-plan-display'
import type { ActionPlanExecutionDetail } from '../types'

type ActionPlanExecutionDetailPoleSummarySectionProps = {
  execution: ActionPlanExecutionDetail
}

export function ActionPlanExecutionDetailPoleSummarySection({
  execution,
}: ActionPlanExecutionDetailPoleSummarySectionProps) {
  const summaries = buildActionPlanPoleTaskSummaries(execution)

  if (summaries.length === 0) {
    return null
  }

  return (
    <TerrainCard className="space-y-2">
      {summaries.map((summary) => (
        <div
          key={summary.businessUnitId}
          className="flex flex-wrap items-center gap-2 text-sm text-[#1a1a1a]"
        >
          <span className="text-[#7D7B75]">
            {summary.role === 'pilot' ? 'Pôle pilote :' : 'Pôle contributeur :'}
          </span>
          <HoustonBadge variant="gray" className="rounded-full text-[10px]">
            {summary.label}
          </HoustonBadge>
          <span className="text-[#7D7B75]">
            Tâche {summary.treated}/{summary.total}
          </span>
        </div>
      ))}
    </TerrainCard>
  )
}
