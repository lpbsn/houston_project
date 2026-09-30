import { Button } from '@/components/ui/button'
import { TerrainStickyFooter } from '@/components/ui/terrain'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type SignalDetailStickyFooterProps = {
  onCreateActionPlan: () => void
  /** Slightly quieter when a pending resolution request already exposes its own actions. */
  subdued?: boolean
  className?: string
  'data-testid'?: string
}

/** Flex-pinned footer: sits under a scrollable details pane (report-page pattern). */
export function SignalDetailStickyFooter({
  className,
  onCreateActionPlan,
  subdued = false,
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
        variant={subdued ? 'outline' : 'default'}
        className={cn(
          'w-full rounded-xl',
          subdued
            ? 'h-10 border-[#E8E6DF] bg-white text-[13px] font-medium text-[#114660] hover:bg-[#F5F4F0] hover:text-[#114660]'
            : cn(
                'h-12 text-[15px] font-semibold text-white',
                terrainBrandAction.bg,
                terrainBrandAction.hover,
              ),
        )}
        onClick={onCreateActionPlan}
      >
        + Créer un plan
      </Button>
    </TerrainStickyFooter>
  )
}
