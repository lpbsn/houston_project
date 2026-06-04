import type { PropsWithChildren } from 'react'

import { cn } from '@/lib/utils'

type TerrainHubSubheaderProps = PropsWithChildren<{
  className?: string
}>

export function TerrainHubSubheader({ children, className }: TerrainHubSubheaderProps) {
  return (
    <div className={cn('shrink-0 border-b border-[#E8E6DF] bg-white', className)}>
      {children}
    </div>
  )
}
