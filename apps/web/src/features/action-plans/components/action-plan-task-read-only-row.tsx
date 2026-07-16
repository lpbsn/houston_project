import {
  formatActionPlanTaskAssigneePoleLine,
  formatActionPlanTaskDeadlineLabel,
} from '@/features/action-plans/lib/action-plan-display'
import type { ActionPlanTaskTemplate } from '@/features/action-plans/types'

import { ActionPlanTaskDetailLayout } from './action-plan-task-detail-layout'

type ActionPlanTaskReadOnlyRowProps = {
  task: ActionPlanTaskTemplate
}

export function ActionPlanTaskReadOnlyRow({ task }: ActionPlanTaskReadOnlyRowProps) {
  const poleLabel = task.business_unit?.specific_name ?? null
  const deadlineLabel = formatActionPlanTaskDeadlineLabel(task.deadline_at)
  const assigneePoleLine = formatActionPlanTaskAssigneePoleLine({
    assigneeDisplayName: task.assigned_display_name,
    poleLabel,
  })

  return (
    <ActionPlanTaskDetailLayout
      leading={<span className="flex h-10 w-10 shrink-0" aria-hidden />}
      title={<p className="text-sm font-medium text-[#1a1a1a]">{task.task}</p>}
      meta={assigneePoleLine}
      deadline={deadlineLabel ? `Échéance : ${deadlineLabel}` : null}
      description={task.description || null}
    />
  )
}
