import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'
import { cn } from '@/lib/utils'

import { flattenActionPlanAssignees } from '../lib/action-plan-display'
import type { ActionPlanExecutionDetail } from '../types'

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
    <section className="flex flex-col gap-1.5">
      <TerrainSectionLabel>Assignés</TerrainSectionLabel>
      <TerrainCard>
        <ul className="flex flex-wrap gap-x-4 gap-y-3" aria-label="Assignés">
          {assignees.map((assignee, index) => {
            const isCurrentUser = currentMembershipId === assignee.membership_id
            return (
              <li key={assignee.membership_id} className="flex min-w-0 items-center gap-2">
                <div
                  className={cn(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px] font-bold',
                    getAvatarClass(index),
                  )}
                  aria-hidden
                >
                  {getDisplayNameInitials(assignee.display_name)}
                </div>
                <span className="truncate text-sm text-[#1a1a1a]">
                  {assignee.display_name}
                  {isCurrentUser ? (
                    <span className="text-[#7D7B75]"> (vous)</span>
                  ) : null}
                </span>
              </li>
            )
          })}
        </ul>
      </TerrainCard>
    </section>
  )
}
