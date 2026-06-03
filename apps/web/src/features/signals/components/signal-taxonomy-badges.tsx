import { Badge } from '@/components/ui/badge'

type SignalTaxonomyBadgesProps = {
  domainKey: string
  subjectKey: string
}

export function SignalTaxonomyBadges({ domainKey, subjectKey }: SignalTaxonomyBadgesProps) {
  const domainLabel = domainKey.split('__').pop() ?? domainKey
  return (
    <div className="flex flex-wrap gap-1.5">
      <Badge variant="secondary" className="rounded-full bg-[#eef2ff] text-[#1b4fd8]">
        {domainLabel}
      </Badge>
      <Badge variant="outline" className="rounded-full border-[#e7dfd1] text-[#6b5f52]">
        {subjectKey.split('__').pop() ?? subjectKey}
      </Badge>
    </div>
  )
}
