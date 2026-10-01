import { useEffect, useId, useRef, type ReactNode } from 'react'

import { isTopNativeOverlay, registerNativeOverlayDismiss } from '@/lib/native-overlay-dismiss'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

function listFocusable(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (node) => !node.hasAttribute('disabled') && node.tabIndex >= 0,
  )
}

type TerrainBottomSheetProps = {
  title: string
  open: boolean
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
  dismissible?: boolean
}

export function TerrainBottomSheet({
  title,
  open,
  onClose,
  children,
  footer,
  dismissible = true,
}: TerrainBottomSheetProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const previouslyFocused = useRef<HTMLElement | null>(null)
  const overlayDismissRef = useRef<(() => void | boolean) | null>(null)

  useEffect(() => {
    if (!open) {
      overlayDismissRef.current = null
      return
    }
    const dismiss = () => {
      if (!dismissible) {
        return false
      }
      onClose()
    }
    overlayDismissRef.current = dismiss
    const unregister = registerNativeOverlayDismiss(dismiss)
    return () => {
      overlayDismissRef.current = null
      unregister()
    }
  }, [dismissible, onClose, open])

  useEffect(() => {
    if (!open) {
      return
    }
    previouslyFocused.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    dialogRef.current?.focus()
    return () => {
      const node = previouslyFocused.current
      if (node && document.contains(node)) {
        node.focus()
      }
    }
  }, [open])

  useEffect(() => {
    if (!open) {
      return
    }
    function onKeyDown(event: KeyboardEvent) {
      const dismiss = overlayDismissRef.current
      if (!dismiss || !isTopNativeOverlay(dismiss)) {
        return
      }
      if (event.key === 'Escape') {
        event.stopImmediatePropagation()
        if (dismissible) {
          onClose()
        }
        return
      }
      if (event.key !== 'Tab') {
        return
      }
      const root = dialogRef.current
      if (!root) {
        return
      }
      const focusable = listFocusable(root)
      if (focusable.length === 0) {
        event.preventDefault()
        root.focus()
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement
      const inside = active instanceof Node && root.contains(active)
      if (event.shiftKey) {
        if (active === first || active === root || !inside) {
          event.preventDefault()
          last.focus()
        }
        return
      }
      if (active === last || active === root || !inside) {
        event.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', onKeyDown, true)
    return () => window.removeEventListener('keydown', onKeyDown, true)
  }, [dismissible, onClose, open])

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      <button
        type="button"
        className="absolute inset-0 bg-black/40"
        disabled={!dismissible}
        aria-label={dismissible ? 'Fermer' : undefined}
        onClick={dismissible ? onClose : undefined}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          'relative z-10 flex max-h-[70vh] flex-col rounded-t-2xl border border-[#E8E6DF] bg-white shadow-lg outline-none',
          terrain.foreground,
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
        <div
          className={cn(
            'min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-4 pt-3',
            footer ? 'pb-3' : 'pb-[max(0.75rem,var(--app-safe-bottom))]',
          )}
        >
          {children}
        </div>
        {footer ? (
          <div className="shrink-0 border-t border-[#E8E6DF] px-4 pt-3 pb-[max(0.75rem,var(--app-safe-bottom))]">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  )
}
