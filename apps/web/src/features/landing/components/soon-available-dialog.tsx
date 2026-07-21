import { useEffect, useId, useRef } from 'react'

type SoonAvailableDialogProps = {
  open: boolean
  message: string
  onClose: () => void
}

export function SoonAvailableDialog({ open, message, onClose }: SoonAvailableDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    if (open) {
      if (!dialog.open) {
        if (typeof dialog.showModal === 'function') {
          dialog.showModal()
        } else {
          dialog.setAttribute('open', '')
        }
      }
    } else if (dialog.open) {
      if (typeof dialog.close === 'function') {
        dialog.close()
      } else {
        dialog.removeAttribute('open')
      }
    }
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      className="fixed inset-0 m-auto max-w-sm rounded-2xl border-0 bg-white p-0 text-spore-forest shadow-2xl backdrop:bg-spore-forest/40 open:flex open:flex-col"
      onClose={onClose}
      onClick={(event) => {
        if (event.target === dialogRef.current) {
          onClose()
        }
      }}
    >
      <div className="flex flex-col gap-4 p-6">
        <h2 id={titleId} className="text-lg font-semibold text-spore-forest">
          Bientôt disponible
        </h2>
        <p className="text-sm leading-relaxed text-spore-moss">{message}</p>
        <button
          type="button"
          className="landing-cta-glow mt-1 inline-flex items-center justify-center rounded-full bg-spore-neon px-5 py-2.5 text-sm font-semibold text-spore-forest transition hover:brightness-105"
          onClick={onClose}
        >
          Compris
        </button>
      </div>
    </dialog>
  )
}
