import { forwardRef, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

type TerrainStickyFooterVariant = 'default' | 'transparent'

type TerrainStickyFooterProps = {
  children: ReactNode
  variant?: TerrainStickyFooterVariant
  className?: string
  'data-testid'?: string
}

export const TerrainStickyFooter = forwardRef<HTMLElement, TerrainStickyFooterProps>(
  function TerrainStickyFooter(
    { children, variant = 'default', className, 'data-testid': dataTestId },
    ref,
  ) {
    return (
      <footer
        ref={ref}
        data-testid={dataTestId}
        className={cn(
          'sticky bottom-0 z-10 mt-auto shrink-0',
          'px-3 pt-2.5 pb-[max(0.75rem,env(safe-area-inset-bottom))]',
          variant === 'default' && [
            'border-t border-[#E8E6DF] bg-[#F5F4F0]',
            'shadow-[0_-4px_12px_rgba(0,0,0,0.04)]',
          ],
          className,
        )}
      >
        {children}
      </footer>
    )
  },
)
