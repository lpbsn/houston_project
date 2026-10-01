import { TerrainStickyFooter } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const catalogPrimaryButtonClassName = cn(
  'text-white',
  terrainBrandAction.bg,
  terrainBrandAction.hover,
)

type ActionPlanTemplateDetailStickyFooterProps = {
  disabled?: boolean
  onUse: () => void
  className?: string
}

export function ActionPlanTemplateDetailStickyFooter({
  className,
  disabled = false,
  onUse,
}: ActionPlanTemplateDetailStickyFooterProps) {
  return (
    <TerrainStickyFooter className={className}>
      <Button
        type="button"
        className={cn('h-11 w-full rounded-full', catalogPrimaryButtonClassName)}
        disabled={disabled}
        onClick={onUse}
      >
        Utiliser ce modèle
      </Button>
    </TerrainStickyFooter>
  )
}
