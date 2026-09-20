import { useEffect, useId, useRef, type ReactNode } from 'react'

type PlatformDialogProps = {
  open: boolean
  title: string
  onClose: () => void
  closeDisabled?: boolean
  children: ReactNode
}

export function PlatformDialog({
  open,
  title,
  onClose,
  closeDisabled = false,
  children,
}: PlatformDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) {
      return
    }
    if (open) {
      if (!dialog.open && typeof dialog.showModal === 'function') {
        dialog.showModal()
      }
    } else if (dialog.open && typeof dialog.close === 'function') {
      dialog.close()
    }
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      className="fixed inset-0 m-auto w-[min(100%,28rem)] rounded-xl border border-[var(--platform-border)] bg-[var(--platform-surface)] p-0 text-[var(--platform-text)] shadow-xl backdrop:bg-[color-mix(in_srgb,var(--platform-nav)_45%,transparent)] open:flex open:flex-col"
      onCancel={(event) => {
        if (closeDisabled) {
          event.preventDefault()
          return
        }
        onClose()
      }}
      onClose={() => {
        if (!closeDisabled) {
          onClose()
        }
      }}
      onClick={(event) => {
        if (event.target !== dialogRef.current || closeDisabled) {
          return
        }
        onClose()
      }}
    >
      {open ? (
        <div className="flex flex-col gap-4 p-6">
          <h2 id={titleId} className="text-lg font-semibold">
            {title}
          </h2>
          {children}
        </div>
      ) : null}
    </dialog>
  )
}
