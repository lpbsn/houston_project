import { HoustonBadge } from '@/components/ui/terrain'
import { actionPlanExecutionDetailNavyBgClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { formatActionPlanExecutionStatusLabel } from '../lib/action-plan-display'

type ActionPlanStatusBadgeProps = {
  status: string
  variant?: 'default' | 'detail' | 'executionHeader'
}

const DETAIL_BADGE_CLASS = 'rounded-full px-2.5 py-1 text-[10px]'
const EXECUTION_HEADER_BADGE_CLASS = 'rounded-full px-2.5 py-1 text-[10px]'

function getBadgeVariant(status: string) {
  if (status === 'done') {
    return 'green'
  }
  if (status === 'canceled') {
    return 'gray'
  }
  if (status === 'pending_validation') {
    return 'amber'
  }
  if (status === 'in_progress') {
    return 'teal'
  }
  return 'blue'
}

export function ActionPlanStatusBadge({
  status,
  variant = 'default',
}: ActionPlanStatusBadgeProps) {
  const badgeVariant = getBadgeVariant(status)
  const isExecutionHeaderInProgress = variant === 'executionHeader' && status === 'in_progress'

  return (
    <HoustonBadge
      variant={badgeVariant}
      className={cn(
        variant === 'detail' && DETAIL_BADGE_CLASS,
        variant === 'executionHeader' && EXECUTION_HEADER_BADGE_CLASS,
        isExecutionHeaderInProgress && actionPlanExecutionDetailNavyBgClassName,
        isExecutionHeaderInProgress && 'text-white',
      )}
    >
      {formatActionPlanExecutionStatusLabel(status)}
    </HoustonBadge>
  )
}
