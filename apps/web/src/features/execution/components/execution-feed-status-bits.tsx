import { Star } from 'lucide-react'

import { HoustonBadge } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

const STAR_VALUES = [1, 2, 3, 4, 5] as const

export function ExecutionFeedDelayChip({ label }: { label: string }) {
  return (
    <HoustonBadge variant="red" className="shrink-0 normal-case tracking-normal">
      {label}
    </HoustonBadge>
  )
}

export function ExecutionFeedReviewStars({ stars }: { stars: number }) {
  return (
    <div
      className="mt-1.5 flex items-center gap-0.5"
      role="img"
      aria-label={`Note : ${stars} sur 5`}
    >
      {STAR_VALUES.map((value) => {
        const filled = stars >= value
        return (
          <Star
            key={value}
            className={cn(
              'size-3.5',
              filled ? 'fill-current text-[#EF9F27]' : 'fill-none text-[#C9C6BD]',
            )}
            strokeWidth={1.5}
            aria-hidden
          />
        )
      })}
    </div>
  )
}
