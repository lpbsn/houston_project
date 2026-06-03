import type { HoustonBadgeVariant } from '@/lib/terrain-styles'
import { HoustonBadge } from '@/components/ui/terrain'

type SignalStatusBadgeProps = {
  status: string
  /** @deprecated Reserved for detail page; styling is shared with feed. */
  variant?: 'feed' | 'detail'
}

const LABELS: Record<string, string> = {
  open: 'EN ATTENTE',
  in_progress: 'EN COURS',
  resolved: 'RÉSOLU',
  archived: 'ARCHIVÉ',
}

const BADGE_VARIANTS: Record<string, HoustonBadgeVariant> = {
  open: 'gray',
  in_progress: 'blue',
  resolved: 'green',
  archived: 'gray',
}

const ARCHIVED_BADGE_CLASS = 'bg-[#555] text-white'

export function SignalStatusBadge({ status }: SignalStatusBadgeProps) {
  const label = LABELS[status] ?? status.toUpperCase()
  const badgeVariant = BADGE_VARIANTS[status] ?? 'gray'

  if (status === 'archived') {
    return <HoustonBadge variant={badgeVariant} className={ARCHIVED_BADGE_CLASS}>{label}</HoustonBadge>
  }

  return <HoustonBadge variant={badgeVariant}>{label}</HoustonBadge>
}
