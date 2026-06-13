import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type TerrainStickyFooterProps = {
  children: ReactNode
  className?: string
}

export function TerrainStickyFooter({ children, className }: TerrainStickyFooterProps) {
  return (
    <footer
      className={cn(
        'sticky bottom-0 z-10 mt-auto shrink-0',
        'border-t border-[#E8E6DF] bg-[#F5F4F0]',
        'shadow-[0_-4px_12px_rgba(0,0,0,0.04)]',
        'px-3 pt-2.5 pb-[max(0.75rem,env(safe-area-inset-bottom))]',
        className,
      )}
    >
      {children}
    </footer>
  )
}
