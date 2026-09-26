import { cn } from '@/lib/utils'

type SignalFeedCardSkeletonProps = {
  className?: string
}

export function SignalFeedCardSkeleton({ className }: SignalFeedCardSkeletonProps) {
  return (
    <div
      className={cn(
        'rounded-[14px] border border-[#E8E6DF] bg-white p-3 border-l-4 border-l-[#E8E6DF]',
        className,
      )}
      aria-hidden
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="h-4 w-16 animate-pulse rounded-full bg-[#EFEDE7]" />
        <div className="h-3 w-10 animate-pulse rounded bg-[#EFEDE7]" />
      </div>
      <div className="h-4 w-[88%] animate-pulse rounded bg-[#EFEDE7]" />
      <div className="mt-2 h-3 w-[55%] animate-pulse rounded bg-[#EFEDE7]" />
      <div className="mt-3 h-3 w-[40%] animate-pulse rounded bg-[#EFEDE7]" />
    </div>
  )
}

type SignalFeedSkeletonListProps = {
  count?: number
  className?: string
}

export function SignalFeedSkeletonList({
  count = 4,
  className,
}: SignalFeedSkeletonListProps) {
  return (
    <div
      className={cn('flex flex-col gap-3 pt-5', className)}
      role="status"
      aria-label="Chargement des observations"
    >
      {Array.from({ length: count }, (_, index) => (
        <SignalFeedCardSkeleton key={index} />
      ))}
    </div>
  )
}
