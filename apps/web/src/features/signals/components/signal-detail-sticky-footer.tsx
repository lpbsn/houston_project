import { Button } from '@/components/ui/button'
import { TerrainStickyFooter } from '@/components/ui/terrain'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type SignalDetailStickyFooterProps = {
  onCreateActionPlan: () => void
  className?: string
}

export function SignalDetailStickyFooter({
  className,
  onCreateActionPlan,
}: SignalDetailStickyFooterProps) {
  return (
    <TerrainStickyFooter className={cn('flex flex-col gap-2', className)}>
      <Button
        type="button"
        className={cn(
          'h-11 w-full rounded-full text-[15px] font-semibold text-white',
          terrainBrandAction.bg,
          terrainBrandAction.hover,
        )}
        onClick={onCreateActionPlan}
      >
        + Plan d&apos;action
      </Button>
    </TerrainStickyFooter>
  )
}
