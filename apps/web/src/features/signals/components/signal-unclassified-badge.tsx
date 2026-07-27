import { HoustonBadge } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import { isSignalMissingResponsibleClassification } from '../lib/signal-unclassified'

type SignalUnclassifiedBadgeProps = {
  signal: {
    responsible_business_unit_id?: string | null
  }
  variant?: 'feed' | 'detail'
  className?: string
}

const LABEL = 'Non classifié'

export function SignalUnclassifiedBadge({
  signal,
  variant = 'detail',
  className,
}: SignalUnclassifiedBadgeProps) {
  if (!isSignalMissingResponsibleClassification(signal)) {
    return null
  }

  if (variant === 'feed') {
    return (
      <span
        className={cn(
          'inline-flex shrink-0 rounded-full bg-[#F4F1EA] px-2 py-0.5 text-[10px] font-medium text-[#5C5346]',
          className,
        )}
      >
        {LABEL}
      </span>
    )
  }

  return (
    <HoustonBadge variant="gray" className={cn('px-2.5 py-1 text-[10px]', className)}>
      {LABEL}
    </HoustonBadge>
  )
}
