import { TerrainCard } from '@/components/ui/terrain'

import type { ActionPlanExecutionDetail } from '../types'
import { ActionPlanExecutionDetailReviewSection } from './action-plan-execution-detail-review-section'

type ActionPlanExecutionDetailTitleSectionProps = {
  execution: ActionPlanExecutionDetail
}

export function ActionPlanExecutionDetailTitleSection({
  execution,
}: ActionPlanExecutionDetailTitleSectionProps) {
  const showReview = execution.validated_at != null && execution.active_review != null

  return (
    <TerrainCard className="space-y-1.5">
      <h1 className="text-lg font-bold leading-snug text-[#222222]">{execution.title}</h1>
      {showReview && execution.active_review ? (
        <ActionPlanExecutionDetailReviewSection activeReview={execution.active_review} embedded />
      ) : null}
    </TerrainCard>
  )
}
