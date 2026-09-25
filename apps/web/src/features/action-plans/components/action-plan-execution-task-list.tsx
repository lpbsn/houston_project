import { useMemo } from 'react'

import { TerrainCard } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import {
  canShowActionPlanTaskCreateObservation,
  canShowActionPlanTaskMarkDone,
  canShowActionPlanTaskSkip,
  canShowActionPlanTaskUnmarkDone,
} from '../lib/action-plan-permission-hints'
import type { ActionPlanTaskExecution } from '../types'
import { ActionPlanExecutionTaskRow } from './action-plan-execution-task-row'

type ActionPlanExecutionTaskListProps = {
  tasks: ActionPlanTaskExecution[]
  isTerminal: boolean
  isMutationPending: boolean
  density?: 'default' | 'compact'
  onMarkDone: (taskId: string) => void
  onUnmarkDone: (taskId: string) => void
  onOpenTaskActions: (task: ActionPlanTaskExecution) => void
}

export function ActionPlanExecutionTaskList({
  tasks,
  isTerminal,
  isMutationPending,
  density = 'default',
  onMarkDone,
  onUnmarkDone,
  onOpenTaskActions,
}: ActionPlanExecutionTaskListProps) {
  const sortedTasks = useMemo(
    () => [...tasks].sort((a, b) => a.position - b.position),
    [tasks],
  )

  const isCompact = density === 'compact'

  return (
    <div className={isCompact ? 'divide-y divide-[#E8E6DF]' : 'space-y-3'}>
      {sortedTasks.map((task) => {
        const row = (
          <ActionPlanExecutionTaskRow
            task={task}
            density={density}
            canShowMarkDone={
              !isTerminal && canShowActionPlanTaskMarkDone(task.permission_hints, { isTerminal, task })
            }
            canShowUnmarkDone={
              !isTerminal &&
              canShowActionPlanTaskUnmarkDone(task.permission_hints, { isTerminal, task })
            }
            canShowSecondaryActions={
              !isTerminal &&
              (canShowActionPlanTaskSkip(task.permission_hints, { isTerminal, task }) ||
                canShowActionPlanTaskCreateObservation(task.permission_hints, {
                  isTerminal,
                  task,
                }))
            }
            isMutationPending={isMutationPending}
            onMarkDone={() => onMarkDone(task.id)}
            onUnmarkDone={() => onUnmarkDone(task.id)}
            onOpenActions={() => onOpenTaskActions(task)}
          />
        )

        if (isCompact) {
          return <div key={task.id}>{row}</div>
        }

        return (
          <TerrainCard
            key={task.id}
            className={cn('p-0', task.status === 'done' && 'shadow-sm')}
          >
            {row}
          </TerrainCard>
        )
      })}
    </div>
  )
}
