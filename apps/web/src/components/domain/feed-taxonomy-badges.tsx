import { HoustonBadge } from '@/components/ui/terrain'
import {
  getFeedDomainBadgeLabel,
  getFeedModuleBadgeLabel,
  getFeedSubjectBadgeLabel,
} from '@/features/signals/lib/signal-display'
import {
  feedTaxonomyDomainBadgeClassName,
  feedTaxonomyModuleBadgeClassName,
} from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type FeedTaxonomyBadgesProps = {
  moduleKey: string
  domainKey: string
  subjectKey: string
  className?: string
}

export function FeedTaxonomyBadges({
  moduleKey,
  domainKey,
  subjectKey,
  className,
}: FeedTaxonomyBadgesProps) {
  const moduleLabel = getFeedModuleBadgeLabel(moduleKey)
  const domainLabel = getFeedDomainBadgeLabel(domainKey)
  const subjectLabel = getFeedSubjectBadgeLabel(subjectKey)

  if (!moduleLabel && !domainLabel && !subjectLabel) {
    return null
  }

  return (
    <span className={cn('inline-flex flex-wrap gap-1', className)}>
      {moduleLabel ? (
        <HoustonBadge variant="gray" className={feedTaxonomyModuleBadgeClassName}>
          {moduleLabel}
        </HoustonBadge>
      ) : null}
      {domainLabel ? (
        <HoustonBadge variant="gray" className={feedTaxonomyDomainBadgeClassName}>
          {domainLabel}
        </HoustonBadge>
      ) : null}
      {subjectLabel ? <HoustonBadge variant="gray">{subjectLabel}</HoustonBadge> : null}
    </span>
  )
}
