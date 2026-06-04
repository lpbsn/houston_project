import { ArrowLeft } from 'lucide-react'

import type { TerrainDetailTitleLayout } from '@/app/terrain-routes'
import { HoustonLogo } from '@/components/domain/houston-logo'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type TerrainTopbarProps = {
  variant: 'hub' | 'detail'
  title?: string
  pageTitle?: string
  detailTitleLayout?: TerrainDetailTitleLayout
  onBack?: () => void
  showBottomBorder?: boolean
}

export function TerrainTopbar({
  variant,
  title,
  pageTitle,
  detailTitleLayout = 'centered',
  onBack,
  showBottomBorder = true,
}: TerrainTopbarProps) {
  if (variant === 'hub') {
    return (
      <header
        className={cn(
          'shrink-0 bg-white',
          showBottomBorder && 'border-b border-[#E8E6DF]',
          'pt-[max(0.75rem,env(safe-area-inset-top))] pb-1.5',
        )}
      >
        <div className="flex flex-col gap-0.5 px-3">
          <div className="flex h-16 items-center justify-center">
            <HoustonLogo />
          </div>
          {pageTitle ? (
            <h1 className="text-left text-xl font-semibold leading-tight text-[#1a1a1a]">
              {pageTitle}
            </h1>
          ) : null}
        </div>
      </header>
    )
  }

  if (detailTitleLayout === 'belowBack') {
    return (
      <header
        className={cn(
          'shrink-0 border-b border-[#E8E6DF] bg-white',
          'pt-[max(0.75rem,env(safe-area-inset-top))] pb-3',
        )}
      >
        <div className="px-4">
          {onBack ? (
            <Button
              type="button"
              variant="ghost"
              className="h-auto px-0 text-sm font-medium text-[#1B4FD8] hover:bg-transparent hover:text-[#1B4FD8]/90"
              onClick={onBack}
            >
              <ArrowLeft className="mr-1 h-4 w-4" />
              Retour
            </Button>
          ) : null}
          {title ? (
            <h1 className="mt-2 text-xl font-semibold text-[#1a1a1a]">{title}</h1>
          ) : null}
        </div>
      </header>
    )
  }

  return (
    <header
      className={cn(
        'shrink-0 border-b border-[#E8E6DF] bg-white',
        'pt-[max(0.75rem,env(safe-area-inset-top))] pb-3',
      )}
    >
      <div className="flex items-center justify-between gap-3 px-4">
        {onBack ? (
          <Button
            type="button"
            variant="ghost"
            className="h-auto px-0 text-sm font-medium text-[#1B4FD8] hover:bg-transparent hover:text-[#1B4FD8]/90"
            onClick={onBack}
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Retour
          </Button>
        ) : (
          <span className="w-16" aria-hidden />
        )}
        <span className="text-sm font-medium text-[#1a1a1a]">{title ?? 'Signal'}</span>
        <span className="w-16" aria-hidden />
      </div>
    </header>
  )
}
