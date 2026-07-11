import {
  actionPlanFeedTealBgClassName,
  terrain,
} from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

export type ActionPlanFeedTaskProgressBarVariant = 'teal' | 'success' | 'muted'

type ActionPlanFeedTaskProgressBarProps = {
  total: number
  filled: number
  fractionLabel: string
  variant?: ActionPlanFeedTaskProgressBarVariant
  className?: string
}

const FILLED_SEGMENT_CLASS: Record<ActionPlanFeedTaskProgressBarVariant, string> = {
  teal: actionPlanFeedTealBgClassName,
  success: terrain.successBg,
  muted: 'bg-[#7D7B75]',
}

export function ActionPlanFeedTaskProgressBar({
  total,
  filled,
  fractionLabel,
  variant = 'teal',
  className,
}: ActionPlanFeedTaskProgressBarProps) {
  const filledSegmentClassName = FILLED_SEGMENT_CLASS[variant]

  return (
    <div className={cn('mt-2 flex items-center gap-2', className)}>
      <div
        className="flex min-w-0 flex-1 gap-0.5"
        role="progressbar"
        aria-valuenow={filled}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label={`Progression des tâches : ${fractionLabel}`}
      >
        {Array.from({ length: total }, (_, index) => (
          <span
            key={index}
            className={cn(
              'h-1.5 min-w-[4px] flex-1 rounded-full',
              index < filled ? filledSegmentClassName : 'bg-[#F0EFE9]',
            )}
          />
        ))}
      </div>
      <span className="shrink-0 text-[11px] tabular-nums text-[#888]">{fractionLabel}</span>
    </div>
  )
}
