import type { PropsWithChildren, ReactNode } from 'react'

import { cn } from '@/lib/utils'

type TerrainHubViewToolbarProps = PropsWithChildren<{
  trailing?: ReactNode
  className?: string
}>

export function TerrainHubViewToolbar({
  children,
  trailing,
  className,
}: TerrainHubViewToolbarProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 px-3 pb-2 pt-0',
        className,
      )}
    >
      <div className="min-w-0 flex-1 overflow-hidden">{children}</div>
      {trailing ? <div className="shrink-0">{trailing}</div> : null}
    </div>
  )
}
