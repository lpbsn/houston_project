import { FeedTaxonomyBadges } from '@/components/domain/feed-taxonomy-badges'

type SignalTaxonomyBadgesProps = {
  domainKey: string
  subjectKey: string
  moduleKey?: string
  className?: string
}

export function SignalTaxonomyBadges({
  domainKey,
  subjectKey,
  moduleKey = '',
  className,
}: SignalTaxonomyBadgesProps) {
  return (
    <FeedTaxonomyBadges
      moduleKey={moduleKey}
      domainKey={domainKey}
      subjectKey={subjectKey}
      className={className}
    />
  )
}
