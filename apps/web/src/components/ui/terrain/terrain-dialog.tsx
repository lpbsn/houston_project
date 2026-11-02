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

type TerrainDialogProps = {
  title: string
  description?: ReactNode
  open: boolean
  onClose: () => void
  children: ReactNode
  dismissible?: boolean
  testId?: string
  size?: 'default' | 'wide'
}

export function TerrainDialog({
  title,
  description,
  open,
  onClose,
  children,
  dismissible = true,
  testId,
  size = 'default',
}: TerrainDialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  const wide = size === 'wide'
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
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center p-4',
        wide && 'max-[520px]:p-3',
      )}
    >
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
        aria-describedby={description ? descriptionId : undefined}
        tabIndex={-1}
        data-testid={testId}
        className={cn(
          'relative z-10 flex w-full flex-col overflow-y-auto border bg-white outline-none',
          terrain.foreground,
          wide
            ? 'max-h-[calc(100dvh-2rem)] max-w-[860px] rounded-[22px] border-[rgba(224,226,220,0.95)] p-4 shadow-[0_28px_80px_rgba(21,26,23,0.16)] min-[521px]:rounded-3xl min-[521px]:px-[18px] min-[521px]:pt-5 min-[521px]:pb-[18px] min-[741px]:rounded-[28px] min-[741px]:px-7 min-[741px]:pt-7 min-[741px]:pb-6'
            : 'max-h-[90vh] max-w-md rounded-xl border-[#E8E6DF] p-4 shadow-lg',
        )}
      >
        <div
          className={cn(
            'flex shrink-0 justify-between gap-3',
            wide ? 'mb-[18px] items-start max-[520px]:mb-3.5 max-[520px]:gap-3' : 'mb-3 items-center',
          )}
        >
          <div className={cn(wide && 'min-w-0 flex-1')}>
            <h2
              id={titleId}
              className={
                wide
                  ? 'text-[25px] leading-[1.04] font-bold tracking-[-0.04em] text-[#242826] min-[521px]:text-[28px] min-[741px]:text-[34px]'
                  : 'text-sm font-semibold text-[#1a1a1a]'
              }
            >
              {title}
            </h2>
            {description ? (
              <p
                id={descriptionId}
                className={
                  wide
                    ? 'mt-2.5 max-w-[610px] text-sm leading-[1.55] text-[#6f776f] min-[741px]:text-[15px] max-[740px]:max-w-none'
                    : 'mt-1 text-sm text-[#5c564e]'
                }
              >
                {description}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            className={
              wide
                ? 'shrink-0 rounded-md bg-transparent px-1 py-2 text-[15px] font-semibold whitespace-nowrap text-[#6f776f] outline-none focus-visible:ring-2 focus-visible:ring-[#245d4a]/40 disabled:opacity-60 max-[520px]:text-sm'
                : 'rounded-md px-2 py-1 text-sm font-medium text-[#5c564e] hover:bg-[#F5F4F0] disabled:opacity-60'
            }
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
