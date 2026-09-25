import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type ActionPlanExecutionDetailLabelProps = {
  children: ReactNode
  className?: string
}

export function ActionPlanExecutionDetailLabel({
  children,
  className,
}: ActionPlanExecutionDetailLabelProps) {
  return (
    <p
      className={cn(
        'text-[11px] font-bold uppercase tracking-[0.04em] text-[#1a1a1a]',
        className,
      )}
    >
      {children}
    </p>
  )
}
