import type { PropsWithChildren } from 'react'

import { cn } from '@/lib/utils'

type TerrainHubSubheaderProps = PropsWithChildren<{
  className?: string
}>

/** Hub feed toolbar strip under the topbar. No default bottom border — feeds are borderless. */
export function TerrainHubSubheader({ children, className }: TerrainHubSubheaderProps) {
  return <div className={cn('shrink-0 bg-white', className)}>{children}</div>
}
