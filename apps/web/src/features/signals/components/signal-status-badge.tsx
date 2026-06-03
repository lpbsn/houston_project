import { HoustonBadge } from '@/components/ui/terrain'

import { getSignalStatusBadgeVariant } from '../lib/signal-display'

type SignalStatusBadgeProps = {
  status: string
  /** @deprecated Reserved for detail page; styling is shared with feed. */
  variant?: 'feed' | 'detail'
}

const LABELS: Record<string, string> = {
  open: 'En attente',
  in_progress: 'En cours',
  resolved: 'Résolu',
  canceled: 'Annulée',
  archived: 'Archivé',
}

const ARCHIVED_BADGE_CLASS = 'bg-[#555] text-white'

export function SignalStatusBadge({ status }: SignalStatusBadgeProps) {
  const label = LABELS[status] ?? status
  const badgeVariant = getSignalStatusBadgeVariant(status)

  if (status === 'archived') {
    return <HoustonBadge variant={badgeVariant} className={ARCHIVED_BADGE_CLASS}>{label}</HoustonBadge>
  }

  return <HoustonBadge variant={badgeVariant}>{label}</HoustonBadge>
}
