import { HoustonBadge } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import {
  domainLabelFromKey,
  getFeedCategoryLabel,
  subjectLabelFromKey,
} from '../lib/signal-display'

type SignalTaxonomyBadgesProps = {
  domainKey: string
  subjectKey: string
  moduleKey?: string
  /** Show operational subject (Catégorie) only on compact feed cards. */
  compact?: boolean
}

export function SignalTaxonomyBadges({
  domainKey,
  subjectKey,
  moduleKey = '',
  compact = false,
}: SignalTaxonomyBadgesProps) {
  const domainLabel = domainLabelFromKey(domainKey)
  const subjectLabel = subjectLabelFromKey(subjectKey)

  if (compact) {
    const categoryLabel = getFeedCategoryLabel(subjectKey, domainKey, moduleKey)
    if (!categoryLabel) {
      return null
    }
    return <HoustonBadge variant="gray">{categoryLabel}</HoustonBadge>
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      <span
        className={cn(
          'inline-flex items-center rounded px-2 py-0.5 text-[9px] font-bold tracking-[0.03em]',
          'bg-[#EF9F27] text-white',
        )}
      >
        {domainLabel}
      </span>
      <span
        className={cn(
          'inline-flex items-center rounded px-2 py-0.5 text-[9px] font-bold tracking-[0.03em]',
          'bg-[#E8E6DF] text-[#555]',
        )}
      >
        {subjectLabel}
      </span>
    </div>
  )
}
