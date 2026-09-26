import { Button } from '@/components/ui/button'
import { TerrainStickyFooter } from '@/components/ui/terrain'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type SignalDetailStickyFooterProps = {
  onCreateActionPlan: () => void
  className?: string
  'data-testid'?: string
}

/** Flex-pinned footer: sits under a scrollable details pane (report-page pattern). */
export function SignalDetailStickyFooter({
  className,
  onCreateActionPlan,
  'data-testid': dataTestId = 'signal-detail-create-plan-footer',
}: SignalDetailStickyFooterProps) {
  return (
    <TerrainStickyFooter
      data-testid={dataTestId}
      className={cn(
        // Override TerrainStickyFooter sticky/mt-auto — parent flex column owns bottom pin.
        'relative mt-0 flex shrink-0 flex-col gap-2',
        className,
      )}
    >
      <Button
        type="button"
        className={cn(
          'h-12 w-full rounded-xl text-[15px] font-semibold text-white',
          terrainBrandAction.bg,
          terrainBrandAction.hover,
        )}
        onClick={onCreateActionPlan}
      >
        + Créer un plan d&apos;action
      </Button>
    </TerrainStickyFooter>
  )
}
