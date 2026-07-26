import { HoustonBadge } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import { isSignalNeedsQualification } from '../lib/signal-qualify-routing'

type SignalNeedsQualificationBadgeProps = {
  signal: {
    routing_status?: string | null
    status?: string | null
  }
  variant?: 'feed' | 'detail'
  className?: string
}

const LABEL = 'À qualifier'

export function SignalNeedsQualificationBadge({
  signal,
  variant = 'detail',
  className,
}: SignalNeedsQualificationBadgeProps) {
  if (!isSignalNeedsQualification(signal)) {
    return null
  }

  if (variant === 'feed') {
    return (
      <span
        className={cn(
          'inline-flex shrink-0 rounded-full bg-[#EEF3FF] px-2 py-0.5 text-[10px] font-medium text-[#1B4FD8]',
          className,
        )}
      >
        {LABEL}
      </span>
    )
  }

  return (
    <HoustonBadge variant="amber" className={cn('px-2.5 py-1 text-[10px]', className)}>
      {LABEL}
    </HoustonBadge>
  )
}
