import { HoustonBadge } from '@/components/ui/terrain'

export const ACTION_PLAN_PINNED_BADGE_LABEL = 'Épinglé'

export function ActionPlanPinnedBadge() {
  return <HoustonBadge variant="gray">{ACTION_PLAN_PINNED_BADGE_LABEL}</HoustonBadge>
}
