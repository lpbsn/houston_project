import { useEffect, useId, useRef, type ReactNode } from 'react'

import { registerNativeOverlayDismiss } from '@/lib/native-overlay-dismiss'
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

type TerrainDialogProps = {
  title: string
  open: boolean
  onClose: () => void
  children: ReactNode
  dismissible?: boolean
  testId?: string
}

export function TerrainDialog({
  title,
  open,
  onClose,
  children,
  dismissible = true,
  testId,
}: TerrainDialogProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const previouslyFocused = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) {
      return
    }
    if (!dismissible) {
      return registerNativeOverlayDismiss(() => false)
    }
    return registerNativeOverlayDismiss(() => {
      onClose()
    })
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
      if (event.key === 'Escape') {
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
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [dismissible, onClose, open])

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
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
        data-testid={testId}
        className={cn(
          'relative z-10 flex max-h-[90vh] w-full max-w-md flex-col overflow-y-auto rounded-xl border border-[#E8E6DF] bg-white p-4 shadow-lg outline-none',
          terrain.foreground,
        )}
      >
        <div className="mb-3 flex shrink-0 items-center justify-between gap-3">
          <h2 id={titleId} className="text-sm font-semibold text-[#1a1a1a]">
            {title}
          </h2>
          <button
            type="button"
            className="rounded-md px-2 py-1 text-sm font-medium text-[#5c564e] hover:bg-[#F5F4F0] disabled:opacity-60"
            disabled={!dismissible}
            onClick={onClose}
          >
            Fermer
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
