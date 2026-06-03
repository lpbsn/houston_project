import { ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type TerrainTopbarProps = {
  variant: 'hub' | 'detail'
  title?: string
  pageTitle?: string
  onBack?: () => void
  showBottomBorder?: boolean
}

export function TerrainTopbar({
  variant,
  title,
  pageTitle,
  onBack,
  showBottomBorder = true,
}: TerrainTopbarProps) {
  if (variant === 'hub') {
    return (
      <header
        className={cn(
          'shrink-0 bg-white',
          showBottomBorder && 'border-b border-[#E8E6DF]',
          'pt-[max(0.75rem,env(safe-area-inset-top))] pb-3',
        )}
      >
        <div className="flex items-center justify-center px-4">
          <span className="text-lg font-semibold tracking-wide text-[#0A0A0A]">houston</span>
        </div>
        {pageTitle ? (
          <h1 className="mt-2 px-4 text-xl font-semibold text-[#1a1a1a]">{pageTitle}</h1>
        ) : null}
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
        <span className="text-sm font-medium text-[#7D7B75]">{title ?? 'Signal'}</span>
        <span className="w-16" aria-hidden />
      </div>
    </header>
  )
}
