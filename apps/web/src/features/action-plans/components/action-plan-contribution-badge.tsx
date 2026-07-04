import { HoustonBadge } from '@/components/ui/terrain'

import { formatContributionStatusLabel } from '../lib/action-plan-display'

type ActionPlanContributionBadgeProps = {
  status: string
}

export function ActionPlanContributionBadge({ status }: ActionPlanContributionBadgeProps) {
  const label = formatContributionStatusLabel(status)
  if (!label) {
    return null
  }

  const variant = status === 'done' ? 'green' : status === 'in_progress' ? 'blue' : 'gray'
  return <HoustonBadge variant={variant}>{`Contribution : ${label}`}</HoustonBadge>
}
