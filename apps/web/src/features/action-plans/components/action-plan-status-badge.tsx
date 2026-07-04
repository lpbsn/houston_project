import { HoustonBadge } from '@/components/ui/terrain'

import { formatActionPlanExecutionStatusLabel } from '../lib/action-plan-display'

type ActionPlanStatusBadgeProps = {
  status: string
}

export function ActionPlanStatusBadge({ status }: ActionPlanStatusBadgeProps) {
  const variant =
    status === 'done'
      ? 'green'
      : status === 'canceled'
        ? 'gray'
        : status === 'pending_validation'
          ? 'amber'
          : 'blue'

  return (
    <HoustonBadge variant={variant}>{formatActionPlanExecutionStatusLabel(status)}</HoustonBadge>
  )
}
