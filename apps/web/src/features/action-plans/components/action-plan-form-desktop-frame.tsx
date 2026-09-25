import { ArrowLeft } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { useXlViewport } from '@/lib/lg-viewport'
import { terrainBackButtonClassName, terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ActionPlanFormDesktopFrameProps = {
  title: string
  onBack: () => void
  primaryLabel: string
  primaryDisabled?: boolean
  notice?: string | null
  children: ReactNode
}

export function ActionPlanFormDesktopFrame({
  title,
  onBack,
  primaryLabel,
  primaryDisabled = false,
  notice = null,
  children,
}: ActionPlanFormDesktopFrameProps) {
  const placePrimaryInBar = useXlViewport()
  const primary = (
    <Button
      type="submit"
      data-testid="action-plan-form-desktop-primary"
      className={cn(
        'h-9 shrink-0 rounded-lg px-4 text-white',
        terrainBrandAction.bg,
        terrainBrandAction.hover,
      )}
      disabled={primaryDisabled}
    >
      {primaryLabel}
    </Button>
  )

  return (
    <div className="flex min-h-full min-w-0 flex-col">
      <div
        data-testid="action-plan-form-desktop-bar"
        className="flex min-w-0 flex-wrap items-center gap-3 border-b border-[#E8E6DF] bg-white px-4 py-3"
      >
        <Button
          type="button"
          variant="ghost"
          className={terrainBackButtonClassName('shrink-0')}
          onClick={onBack}
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Retour
        </Button>
        <h1 className="min-w-0 flex-1 truncate text-base font-semibold text-[#1a1a1a]">{title}</h1>
        {placePrimaryInBar ? (
          <div className="flex min-w-0 items-center gap-3">
            {notice ? (
              <p
                data-testid="action-plan-form-desktop-notice"
                className="max-w-xs text-right text-xs text-[#555]"
              >
                {notice}
              </p>
            ) : null}
            {primary}
          </div>
        ) : null}
      </div>
      <div className="mx-auto flex w-full min-w-0 max-w-5xl flex-col gap-4 px-4 py-4">
        {children}
        {placePrimaryInBar ? null : (
          <div className="flex min-w-0 flex-col items-stretch gap-2 sm:items-end">
            {notice ? (
              <p data-testid="action-plan-form-desktop-notice" className="text-sm text-[#555]">
                {notice}
              </p>
            ) : null}
            <div className="flex justify-end">{primary}</div>
          </div>
        )}
      </div>
    </div>
  )
}
