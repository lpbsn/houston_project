import { ActionDeadlineProgressBar } from '@/components/domain/action-deadline-progress-bar'
import { TerrainDetailFieldCard } from '@/components/ui/terrain'

import type { ActionDetail } from '../types'

type ActionDetailDeadlineCardProps = {
  action: Pick<ActionDetail, 'created_at' | 'due_at' | 'is_overdue'>
}

export function ActionDetailDeadlineCard({ action }: ActionDetailDeadlineCardProps) {
  return (
    <TerrainDetailFieldCard label="Deadline">
      <ActionDeadlineProgressBar
        createdAt={action.created_at}
        dueAt={action.due_at}
        isOverdue={action.is_overdue}
      />
    </TerrainDetailFieldCard>
  )
}
