import { HoustonBadge } from '@/components/ui/terrain'
import { terrainInProgress } from '@/lib/terrain-styles'
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
  interesting: 'Intéressant',
  resolved: 'Résolue',
  canceled: 'Annulée',
  archived: 'Archivée',
}

const ARCHIVED_BADGE_CLASS = 'bg-[#555] text-white'

const DETAIL_BADGE_CLASS = 'px-2.5 py-1 text-[10px]'

const FEED_STATUS_CLASS: Record<string, string> = {
  open: 'bg-[#FFF4E5] text-[#B45309]',
  in_progress: terrainInProgress.badgeFeed,
  interesting: 'bg-[#EEF2FF] text-[#1B4FD8]',
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
      <HoustonBadge variant={badgeVariant} className={cn(DETAIL_BADGE_CLASS, ARCHIVED_BADGE_CLASS)}>
        {label}
      </HoustonBadge>
    )
  }

  return (
    <HoustonBadge variant={badgeVariant} className={DETAIL_BADGE_CLASS}>
      {label}
    </HoustonBadge>
  )
}
