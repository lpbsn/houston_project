import { Button } from '@/components/ui/button'
import { TerrainStickyFooter } from '@/components/ui/terrain'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type SignalDetailStickyFooterProps = {
  onCreateActionPlan: () => void
}

export function SignalDetailStickyFooter({ onCreateActionPlan }: SignalDetailStickyFooterProps) {
  return (
    <TerrainStickyFooter className="flex flex-col gap-2">
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
