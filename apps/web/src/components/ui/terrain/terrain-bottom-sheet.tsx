import { useId, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

type TerrainBottomSheetProps = {
  title: string
  open: boolean
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}

export function TerrainBottomSheet({
  title,
  open,
  onClose,
  children,
  footer,
}: TerrainBottomSheetProps) {
  const titleId = useId()

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      <button
        type="button"
        className="absolute inset-0 bg-black/40"
        aria-label="Fermer"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cn(
          'relative z-10 flex max-h-[70vh] flex-col rounded-t-2xl border border-[#E8E6DF] bg-white shadow-lg',
        )}
      >
        <div className="flex shrink-0 items-center justify-center py-2">
          <span className="h-1 w-10 rounded-full bg-[#E8E6DF]" />
        </div>
        <div className="shrink-0 border-b border-[#E8E6DF] px-4 pb-3">
          <h2 id={titleId} className="text-sm font-semibold text-[#1a1a1a]">
            {title}
          </h2>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-4 py-3">
          {children}
        </div>
        {footer ? (
          <div className="shrink-0 border-t border-[#E8E6DF] px-4 py-3">{footer}</div>
        ) : null}
      </div>
    </div>
  )
}
