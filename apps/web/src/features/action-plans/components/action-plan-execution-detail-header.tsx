import type { ActionPlanExecutionDetail } from '../types'
import { ActionPlanExecutionDetailDeadlineSection } from './action-plan-execution-detail-deadline-section'
import { ActionPlanExecutionDetailTitleSection } from './action-plan-execution-detail-title-section'
import { isActionPlanExecutionTerminal } from '../lib/action-plan-display'

type ActionPlanExecutionDetailHeaderProps = {
  execution: ActionPlanExecutionDetail
  isOverdue: boolean
}

export function ActionPlanExecutionDetailHeader({
  execution,
  isOverdue,
}: ActionPlanExecutionDetailHeaderProps) {
  return (
    <>
      <ActionPlanExecutionDetailTitleSection execution={execution} />
      <ActionPlanExecutionDetailDeadlineSection
        execution={execution}
        isOverdue={isOverdue}
        isTerminal={isActionPlanExecutionTerminal(execution.status)}
      />
    </>
  )
}
