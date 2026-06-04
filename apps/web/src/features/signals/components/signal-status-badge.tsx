import { HoustonBadge } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import { getSignalStatusBadgeVariant } from '../lib/signal-display'

type SignalStatusBadgeProps = {
  status: string
  variant?: 'feed' | 'detail'
  className?: string
}

const LABELS: Record<string, string> = {
  open: 'En attente',
  in_progress: 'En cours',
  resolved: 'Résolu',
  canceled: 'Annulée',
  archived: 'Archivé',
}

const ARCHIVED_BADGE_CLASS = 'bg-[#555] text-white'

const FEED_STATUS_CLASS: Record<string, string> = {
  open: 'bg-[#FFF4E5] text-[#B45309]',
  in_progress: 'bg-[#E8F0FE] text-[#1B4FD8]',
  resolved: 'bg-[#E6F4EA] text-[#137333]',
  canceled: 'bg-[#F0EFE9] text-[#7D7B75]',
  archived: 'bg-[#F0EFE9] text-[#7D7B75]',
}

export function SignalStatusBadge({
  status,
  variant = 'detail',
  className,
}: SignalStatusBadgeProps) {
  const label = LABELS[status] ?? status

  if (variant === 'feed') {
    return (
      <span
        className={cn(
          'inline-flex shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium',
          FEED_STATUS_CLASS[status] ?? 'bg-[#F0EFE9] text-[#444]',
          className,
        )}
      >
        {label}
      </span>
    )
  }

  const badgeVariant = getSignalStatusBadgeVariant(status)

  if (status === 'archived') {
    return (
      <HoustonBadge variant={badgeVariant} className={ARCHIVED_BADGE_CLASS}>
        {label}
      </HoustonBadge>
    )
  }

  return <HoustonBadge variant={badgeVariant}>{label}</HoustonBadge>
}
