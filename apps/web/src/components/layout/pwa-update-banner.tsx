import { Button } from '@/components/ui/button'
import { applyPwaUpdate, dismissPwaUpdate, usePwaUpdate } from '@/lib/pwa-update'
import { terrainStatusBannerClassName } from '@/lib/terrain-styles'

export function PwaUpdateBanner() {
  const { needsRefresh } = usePwaUpdate()

  if (!needsRefresh) {
    return null
  }

  return (
    <div className={terrainStatusBannerClassName('flex items-center justify-center gap-2')} role="status">
      <span className="flex-1">Une nouvelle version est disponible</span>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-7 shrink-0 border-[#E8C88A] bg-white px-2.5 text-xs"
        onClick={() => applyPwaUpdate()}
      >
        Recharger
      </Button>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        className="h-7 shrink-0 px-2.5 text-xs text-[#8A5A00]"
        onClick={() => dismissPwaUpdate()}
      >
        Plus tard
      </Button>
    </div>
  )
}
