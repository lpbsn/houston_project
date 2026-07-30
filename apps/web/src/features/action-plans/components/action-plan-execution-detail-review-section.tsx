import { Star } from 'lucide-react'

import { TerrainCard } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import type { ActionPlanExecutionDetail } from '../types'

const STAR_VALUES = [1, 2, 3, 4, 5] as const

type ActionPlanExecutionDetailReviewSectionProps = {
  activeReview: NonNullable<ActionPlanExecutionDetail['active_review']>
}

function reviewStarsAriaLabel(stars: number): string {
  return `Note : ${stars} sur 5`
}

export function ActionPlanExecutionDetailReviewSection({
  activeReview,
}: ActionPlanExecutionDetailReviewSectionProps) {
  const comment = activeReview.comment.trim()

  return (
    <TerrainCard className="space-y-2">
      <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
        Note
      </p>

      <div
        className="flex items-center gap-1"
        role="img"
        aria-label={reviewStarsAriaLabel(activeReview.stars)}
      >
        {STAR_VALUES.map((value) => {
          const filled = activeReview.stars >= value
          return (
            <Star
              key={value}
              className={cn(
                'size-5',
                filled ? 'fill-current text-[#EF9F27]' : 'fill-none text-[#C9C6BD]',
              )}
              strokeWidth={1.5}
              aria-hidden
            />
          )
        })}
      </div>

      {comment ? <p className="text-sm text-[#555]">{comment}</p> : null}
    </TerrainCard>
  )
}
