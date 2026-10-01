import { getDisplayNameInitials } from '@/lib/display-names'
import { cn } from '@/lib/utils'

import { flattenActionPlanAssignees } from '../lib/action-plan-display'
import type { ActionPlanExecutionDetail } from '../types'

const ASSIGNEES_PER_COLUMN = 4

const AVATAR_BG_CLASSES = [
  'bg-[#EEF2FF] text-[#1B4FD8]',
  'bg-[#FFF4E6] text-[#C76B00]',
  'bg-[#E8F5E9] text-[#2E7D32]',
  'bg-[#FCE4EC] text-[#C2185B]',
  'bg-[#F3E5F5] text-[#7B1FA2]',
]

type ActionPlanExecutionDetailAssigneesSectionProps = {
  execution: ActionPlanExecutionDetail
  currentMembershipId?: string | null
}

function getAvatarClass(index: number): string {
  return AVATAR_BG_CLASSES[index % AVATAR_BG_CLASSES.length] ?? AVATAR_BG_CLASSES[0]
}

export function ActionPlanExecutionDetailAssigneesSection({
  execution,
  currentMembershipId,
}: ActionPlanExecutionDetailAssigneesSectionProps) {
  const assignees = flattenActionPlanAssignees(execution.assignees_by_pole)
  if (assignees.length === 0) {
    return null
  }

  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
        Assignés
      </p>
      <ul
        className="grid grid-flow-col justify-start gap-x-4 gap-y-2"
        style={{ gridTemplateRows: `repeat(${Math.min(ASSIGNEES_PER_COLUMN, assignees.length)}, auto)` }}
        aria-label="Assignés"
      >
        {assignees.map((assignee, index) => {
          const isCurrentUser = currentMembershipId === assignee.membership_id
          return (
            <li key={assignee.membership_id} className="flex min-w-0 items-center gap-2">
              <div
                className={cn(
                  'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[9px] font-bold',
                  getAvatarClass(index),
                )}
                aria-hidden
              >
                {getDisplayNameInitials(assignee.display_name)}
              </div>
              <span className="min-w-0 break-words text-[13px] text-[#1a1a1a]">
                {assignee.display_name}
                {isCurrentUser ? <span className="text-[#7D7B75]"> (vous)</span> : null}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
