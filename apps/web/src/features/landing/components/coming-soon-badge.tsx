import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type ComingSoonBadgeProps = {
  className?: string
  children?: ReactNode
}

export function ComingSoonBadge({
  className,
  children = 'Bientôt disponible',
}: ComingSoonBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border border-spore-neon/40 bg-spore-neon/15 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-spore-forest',
        className,
      )}
    >
      {children}
    </span>
  )
}
