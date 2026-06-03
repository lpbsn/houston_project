import { HoustonBadge } from '@/components/ui/terrain'

type SignalUrgencyBadgeProps = {
  urgency: string
}

export function SignalUrgencyBadge({ urgency }: SignalUrgencyBadgeProps) {
  if (urgency !== 'high') {
    return null
  }
  return <HoustonBadge variant="red">⚠ Urgent</HoustonBadge>
}
