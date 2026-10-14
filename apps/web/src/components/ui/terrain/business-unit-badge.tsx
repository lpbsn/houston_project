import type { ReactNode } from 'react'

import { getBusinessUnitColors } from '@/lib/business-unit-colors'
import { cn } from '@/lib/utils'

type BusinessUnitBadgeProps = {
  colorIndex?: number | null
  children: ReactNode
  className?: string
}

export function BusinessUnitBadge({ colorIndex, children, className }: BusinessUnitBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex max-w-full items-center rounded-md px-2 py-0.5 text-[11px] font-semibold leading-snug',
        className,
      )}
      style={getBusinessUnitColors(colorIndex)}
    >
      {children}
    </span>
  )
}
