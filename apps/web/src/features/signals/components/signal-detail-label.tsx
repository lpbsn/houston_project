import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type SignalDetailLabelProps = {
  children: ReactNode
  className?: string
}

export function SignalDetailLabel({ children, className }: SignalDetailLabelProps) {
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
