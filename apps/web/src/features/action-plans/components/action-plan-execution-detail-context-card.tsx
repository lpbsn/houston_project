import { TerrainCard } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'
import { cn } from '@/lib/utils'

import { flattenActionPlanAssignees } from '../lib/action-plan-display'
import type { ActionPlanExecutionDetail } from '../types'
import { ActionPlanExecutionDetailLabel } from './action-plan-execution-detail-label'
import { ActionPlanStatusBadge } from './action-plan-status-badge'

const AVATAR_BG_CLASSES = [
  'bg-[#EEF2FF] text-[#1B4FD8]',
  'bg-[#FFF4E6] text-[#C76B00]',
  'bg-[#E8F5E9] text-[#2E7D32]',
  'bg-[#FCE4EC] text-[#C2185B]',
  'bg-[#F3E5F5] text-[#7B1FA2]',
]

type ActionPlanExecutionDetailContextCardProps = {
  execution: ActionPlanExecutionDetail
  currentMembershipId?: string | null
}

function getAvatarClass(index: number): string {
  return AVATAR_BG_CLASSES[index % AVATAR_BG_CLASSES.length] ?? AVATAR_BG_CLASSES[0]
}

export function ActionPlanExecutionDetailContextCard({
  execution,
  currentMembershipId,
}: ActionPlanExecutionDetailContextCardProps) {
  const poleLabel = execution.pilot_business_unit.specific_name.trim()
  const creatorName = execution.created_by_display_name.trim()
  const assignees = flattenActionPlanAssignees(execution.assignees_by_pole)

  return (
    <TerrainCard className="space-y-3">
      <ActionPlanExecutionDetailLabel>Contexte</ActionPlanExecutionDetailLabel>
      <ActionPlanStatusBadge
        status={execution.status}
        validatedAt={execution.validated_at}
        variant="executionHeader"
      />
      {poleLabel ? (
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
            Pôle pilote
          </p>
          <p className="text-[13px] leading-relaxed text-[#1a1a1a]">{poleLabel}</p>
        </div>
      ) : null}
      {creatorName ? (
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
            Créateur
          </p>
          <p className="inline-flex max-w-full items-center gap-2 text-[13px] leading-relaxed text-[#1a1a1a]">
            <span
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#F0EFE9] text-[9px] font-bold text-[#5c564e]"
              aria-hidden
            >
              {getDisplayNameInitials(creatorName)}
            </span>
            <span className="min-w-0 break-words">{creatorName}</span>
          </p>
        </div>
      ) : null}
      {assignees.length > 0 ? (
        <div className="space-y-1.5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
            Assignés
          </p>
          <ul className="flex flex-col gap-2" aria-label="Assignés">
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
      ) : null}
    </TerrainCard>
  )
}
