import type { ReactNode } from 'react'
import { ArrowLeft } from 'lucide-react'

import type { TerrainDetailTitleLayout } from '@/app/terrain-routes'
import { useTerrainHubTitleSlotValue } from '@/components/layout/terrain-hub-title-slot'
import { Button } from '@/components/ui/button'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { useLgViewport } from '@/lib/lg-viewport'
import { terrainBackButtonClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TerrainTopbarProps = {
  variant: 'hub' | 'detail'
  title?: string
  pageTitle?: string
  detailTitleLayout?: TerrainDetailTitleLayout
  onBack?: () => void
  showBottomBorder?: boolean
  trailing?: ReactNode
  afterTitle?: ReactNode
}

function TrailingSlot({ trailing }: { trailing?: ReactNode }) {
  if (!trailing) {
    return <span className="w-10" aria-hidden />
  }

  return <div className="flex w-10 justify-end">{trailing}</div>
}

function DetailTrailingSlot({ trailing }: { trailing?: ReactNode }) {
  if (!trailing) {
    return <span className="w-16" aria-hidden />
  }

  return <div className="flex min-w-16 justify-end">{trailing}</div>
}

export function TerrainTopbar({
  variant,
  title,
  pageTitle,
  detailTitleLayout = 'centered',
  onBack,
  showBottomBorder = true,
  trailing,
  afterTitle,
}: TerrainTopbarProps) {
  const slotAfterTitle = useTerrainHubTitleSlotValue()
  const titleAddon = afterTitle ?? slotAfterTitle
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const safeAreaClass = cn(
    'pt-[max(0.75rem,var(--app-safe-top))]',
    isDesktopWeb && 'pt-0 pb-0',
  )

  if (variant === 'hub') {
    return (
      <header
        className={cn(
          'shrink-0 bg-white',
          showBottomBorder && 'border-b border-[#E8E6DF]',
          safeAreaClass,
          !isDesktopWeb && 'pb-1.5',
        )}
      >
        <div
          className={cn(
            'flex min-h-14 items-center justify-between gap-3 px-3',
            isDesktopWeb && 'lg:min-h-16 lg:px-6',
          )}
        >
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1">
            {pageTitle ? (
              <h1 className="min-w-0 truncate text-left text-2xl font-semibold leading-tight text-[#1a1a1a]">
                {pageTitle}
              </h1>
            ) : (
              <span className="min-w-0 flex-1" aria-hidden />
            )}
            {titleAddon ? (
              <div className="min-w-0 shrink">{titleAddon}</div>
            ) : null}
          </div>
          <TrailingSlot trailing={trailing} />
        </div>
      </header>
    )
  }

  if (detailTitleLayout === 'belowBack') {
    return (
      <header
        className={cn(
          'shrink-0 bg-white',
          showBottomBorder && 'border-b border-[#E8E6DF]',
          safeAreaClass,
          !isDesktopWeb && 'pb-3',
        )}
      >
        <div className={cn('px-4', isDesktopWeb && 'lg:px-6')}>
          <div
            className={cn(
              'flex items-start justify-between gap-3',
              isDesktopWeb && 'lg:min-h-16 lg:items-center',
            )}
          >
            <div className="min-w-0 flex-1">
              {onBack ? (
                <Button
                  type="button"
                  variant="ghost"
                  className={terrainBackButtonClassName()}
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
            <DetailTrailingSlot trailing={trailing} />
          </div>
        </div>
      </header>
    )
  }

  return (
    <header
      className={cn(
          'shrink-0 bg-white',
          showBottomBorder && 'border-b border-[#E8E6DF]',
          safeAreaClass,
          !isDesktopWeb && 'pb-3',
        )}
    >
      <div
        className={cn(
          'flex items-center justify-between gap-3 px-4',
          isDesktopWeb && 'lg:h-16 lg:px-6',
        )}
      >
        {onBack ? (
          <Button
            type="button"
            variant="ghost"
            className={terrainBackButtonClassName()}
            onClick={onBack}
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Retour
          </Button>
        ) : (
          <span className="w-16" aria-hidden />
        )}
        <span className="text-sm font-medium text-[#1a1a1a]">{title ?? 'Observation'}</span>
        <DetailTrailingSlot trailing={trailing} />
      </div>
    </header>
  )
}
