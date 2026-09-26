import { cn } from '@/lib/utils'

type ExecutionFeedCardSkeletonProps = {
  className?: string
}

function ExecutionFeedCardSkeleton({ className }: ExecutionFeedCardSkeletonProps) {
  return (
    <div
      className={cn('rounded-[14px] border border-[#E8E6DF] bg-white p-3', className)}
      aria-hidden
    >
      <div className="mb-2 flex items-center gap-2">
        <div className="h-5 w-16 animate-pulse rounded-full bg-[#EFEDE7]" />
        <div className="h-5 w-20 animate-pulse rounded-full bg-[#EFEDE7]" />
      </div>
      <div className="h-4 w-[88%] animate-pulse rounded bg-[#EFEDE7]" />
      <div className="mt-2 h-3 w-[55%] animate-pulse rounded bg-[#EFEDE7]" />
      <div className="mt-3 h-3 w-[40%] animate-pulse rounded bg-[#EFEDE7]" />
    </div>
  )
}

type ExecutionFeedSkeletonListProps = {
  count?: number
  className?: string
}

export function ExecutionFeedSkeletonList({
  count = 3,
  className,
}: ExecutionFeedSkeletonListProps) {
  return (
    <div
      className={cn('flex flex-col gap-3 pt-5', className)}
      role="status"
      aria-label="Chargement des exécutions"
    >
      {Array.from({ length: count }, (_, index) => (
        <ExecutionFeedCardSkeleton key={index} />
      ))}
    </div>
  )
}
