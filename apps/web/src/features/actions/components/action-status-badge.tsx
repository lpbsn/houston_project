import { cn } from '@/lib/utils'

import {
  formatActionExecutionFeedStatusLabel,
  formatActionStatusLabel,
} from '../lib/action-display'

type ActionStatusBadgeProps = {
  status: string
  className?: string
  labelVariant?: 'default' | 'feed'
}

const STATUS_CLASS: Record<string, string> = {
  open: 'bg-[#FFF4E5] text-[#B45309]',
  in_progress: 'bg-[#E8F0FE] text-[#1B4FD8]',
  pending_validation: 'bg-[#FFF4E5] text-[#B45309]',
  reopened: 'bg-[#FFF4E5] text-[#B45309]',
  done: 'bg-[#E6F4EA] text-[#137333]',
  canceled: 'bg-[#F0EFE9] text-[#7D7B75]',
}

export function ActionStatusBadge({
  status,
  className,
  labelVariant = 'default',
}: ActionStatusBadgeProps) {
  const label =
    labelVariant === 'feed'
      ? formatActionExecutionFeedStatusLabel(status)
      : formatActionStatusLabel(status)

  return (
    <span
      className={cn(
        'inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium',
        labelVariant === 'feed' && 'uppercase tracking-[0.02em]',
        STATUS_CLASS[status] ?? 'bg-[#F0EFE9] text-[#444]',
        className,
      )}
    >
      {label}
    </span>
  )
}
