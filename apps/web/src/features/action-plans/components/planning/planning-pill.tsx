import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type PlanningPillProps = {
  active: boolean
  onClick: () => void
  children: ReactNode
  'aria-label'?: string
}

export function PlanningPill({ active, onClick, children, 'aria-label': ariaLabel }: PlanningPillProps) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      aria-pressed={active}
      className={cn(
        'shrink-0 rounded-lg px-2.5 py-1.5 text-sm transition-colors',
        active
          ? 'border border-[#1B4FD8] bg-[#EEF3FF] text-[#1B4FD8]'
          : 'border border-transparent bg-[#F5F4F0] text-[#1a1a1a]',
      )}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
