import { Button } from '@/components/ui/button'
import { TerrainStickyFooter } from '@/components/ui/terrain'
import { terrain } from '@/lib/terrain-styles'
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
          'h-11 w-full rounded-2xl text-[15px] font-semibold text-white hover:bg-[#1B4FD8]/95',
          terrain.primaryBg,
        )}
        onClick={onCreateActionPlan}
      >
        + Plan d&apos;action
      </Button>
    </TerrainStickyFooter>
  )
}
