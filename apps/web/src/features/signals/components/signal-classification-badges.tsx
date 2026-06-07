import { HoustonBadge } from '@/components/ui/terrain'
import {
  formatSignalClassification,
  type SignalClassificationInput,
} from '@/lib/signal-classification'
import { cn } from '@/lib/utils'

type SignalClassificationBadgesProps = {
  signal: SignalClassificationInput
  className?: string
}

export function SignalClassificationBadges({
  signal,
  className,
}: SignalClassificationBadgesProps) {
  const classification = formatSignalClassification(signal)

  if (!classification.primaryLine) {
    return null
  }

  return (
    <span className={cn('inline-flex flex-col gap-0.5', className)}>
      <span className="inline-flex flex-wrap gap-1">
        <HoustonBadge variant="gray">{classification.primaryLine}</HoustonBadge>
      </span>
      {classification.affectedLine ? (
        <span className="text-[11px] text-[#888]">{classification.affectedLine}</span>
      ) : null}
    </span>
  )
}
