import type { ActionPlanExecutionDetail } from '../types'
import { ActionPlanExecutionDetailAssigneesSection } from './action-plan-execution-detail-assignees-section'
import { ActionPlanExecutionDetailDeadlineSection } from './action-plan-execution-detail-deadline-section'
import { ActionPlanExecutionDetailDescriptionSection } from './action-plan-execution-detail-description-section'
import { ActionPlanExecutionDetailReviewSection } from './action-plan-execution-detail-review-section'
import { ActionPlanExecutionDetailTitleSection } from './action-plan-execution-detail-title-section'
import { isActionPlanExecutionTerminal } from '../lib/action-plan-display'

type ActionPlanExecutionDetailHeaderProps = {
  execution: ActionPlanExecutionDetail
  isOverdue: boolean
  currentMembershipId?: string | null
}

export function ActionPlanExecutionDetailHeader({
  execution,
  isOverdue,
  currentMembershipId,
}: ActionPlanExecutionDetailHeaderProps) {
  const isTerminal = isActionPlanExecutionTerminal(execution.status)

  return (
    <div className="flex flex-col gap-2.5">
      <ActionPlanExecutionDetailTitleSection execution={execution} />
      {execution.active_review != null ? (
        <ActionPlanExecutionDetailReviewSection activeReview={execution.active_review} />
      ) : null}
      <ActionPlanExecutionDetailDeadlineSection
        execution={execution}
        isOverdue={isOverdue}
        isTerminal={isTerminal}
      />
      <ActionPlanExecutionDetailAssigneesSection
        execution={execution}
        currentMembershipId={currentMembershipId}
      />
      <ActionPlanExecutionDetailDescriptionSection execution={execution} />
    </div>
  )
}
