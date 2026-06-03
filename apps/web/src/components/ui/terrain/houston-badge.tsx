import type { ReactNode } from 'react'

import {
  houstonBadgeVariants,
  type HoustonBadgeVariant,
} from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type HoustonBadgeProps = {
  variant: HoustonBadgeVariant
  children: ReactNode
  className?: string
}

export function HoustonBadge({ variant, children, className }: HoustonBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-2 py-0.5 text-[9px] font-bold tracking-[0.03em]',
        houstonBadgeVariants[variant],
        className,
      )}
    >
      {children}
    </span>
  )
}
