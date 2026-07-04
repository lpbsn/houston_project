import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'

import type { ActionPlanPoleSection } from '../lib/action-plan-display'
import { shouldShowContributionStatusForPole } from '../lib/action-plan-permission-hints'
import { ActionPlanContributionBadge } from './action-plan-contribution-badge'
import { ActionPlanExecutionTaskRow } from './action-plan-execution-task-row'
import type { ActionPlanTaskExecution } from '../types'

type ActionPlanPoleSectionProps = {
  section: ActionPlanPoleSection
  isTerminal: boolean
  isMutationPending: boolean
  canShowTaskActions: (task: ActionPlanTaskExecution) => boolean
  onMarkDone: (taskId: string) => void
  onCreateObservation: (taskId: string) => void
  onSkipRequest: (taskId: string) => void
}

export function ActionPlanPoleSectionView({
  section,
  isTerminal,
  isMutationPending,
  canShowTaskActions,
  onMarkDone,
  onCreateObservation,
  onSkipRequest,
}: ActionPlanPoleSectionProps) {
  const assigneeNames = section.assignees.map((assignee) => assignee.display_name).join(', ')
  const showContribution = shouldShowContributionStatusForPole({
    contributionStatus: section.contributionStatus,
    taskCount: section.tasks.length,
  })

  return (
    <section className="space-y-2">
      <TerrainSectionLabel>{section.businessUnitLabel}</TerrainSectionLabel>
      <TerrainCard className="space-y-3">
        {showContribution && section.contributionStatus ? (
          <ActionPlanContributionBadge status={section.contributionStatus} />
        ) : null}
        {assigneeNames ? (
          <p className="text-xs text-[#7D7B75]">Assignées : {assigneeNames}</p>
        ) : null}
        {section.tasks.length > 0 ? (
          <div className="space-y-2">
            {section.tasks.map((task) => (
              <ActionPlanExecutionTaskRow
                key={task.id}
                task={task}
                canShowActions={!isTerminal && canShowTaskActions(task)}
                isMutationPending={isMutationPending}
                onMarkDone={() => onMarkDone(task.id)}
                onCreateObservation={() => onCreateObservation(task.id)}
                onSkipRequest={() => onSkipRequest(task.id)}
              />
            ))}
          </div>
        ) : null}
      </TerrainCard>
    </section>
  )
}
