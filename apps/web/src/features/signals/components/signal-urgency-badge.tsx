import { Badge } from '@/components/ui/badge'

type SignalUrgencyBadgeProps = {
  urgency: string
}

export function SignalUrgencyBadge({ urgency }: SignalUrgencyBadgeProps) {
  if (urgency !== 'high') {
    return null
  }
  return (
    <Badge className="rounded-full bg-[#fde8e8] text-[#a32d2d] hover:bg-[#fde8e8]">
      Urgent
    </Badge>
  )
}
