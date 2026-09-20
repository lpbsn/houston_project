import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { PlatformDialog } from '@/features/platform/components/platform-dialog'
import { getCompleteErrorMessage } from '@/features/onboarding/lib/onboarding-draft-errors'

type PlatformDeleteZoneProps = {
  canDelete: boolean
  blockingReasons: string[]
  confirmLabel: string
  isPending: boolean
  onConfirm: (justification: string) => Promise<void> | void
}

export function PlatformDeleteZone({
  canDelete,
  blockingReasons,
  confirmLabel,
  isPending,
  onConfirm,
}: PlatformDeleteZoneProps) {
  const [open, setOpen] = useState(false)
  const [justification, setJustification] = useState('')
  const [error, setError] = useState<string | null>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  const wasOpen = useRef(false)

  useEffect(() => {
    if (wasOpen.current && !open) {
      triggerRef.current?.focus()
    }
    wasOpen.current = open
  }, [open])

  return (
    <section className="mt-10 border-t border-[var(--platform-border)] pt-6">
      <h3 className="text-sm font-semibold text-[var(--platform-status-problem-fg)]">Zone destructive</h3>
      {canDelete ? (
        <>
          <p className="mt-1 text-sm text-[var(--platform-muted)]">
            Cette action est définitive. Une justification est obligatoire.
          </p>
          <Button
            ref={triggerRef}
            type="button"
            variant="destructive"
            className="mt-3 h-10"
            onClick={() => {
              setError(null)
              setOpen(true)
            }}
          >
            {confirmLabel}
          </Button>
          <PlatformDialog
            open={open}
            title={confirmLabel}
            closeDisabled={isPending}
            onClose={() => {
              if (!isPending) {
                setOpen(false)
              }
            }}
          >
            <form
              className="grid gap-3"
              onSubmit={async (event) => {
                event.preventDefault()
                setError(null)
                try {
                  await onConfirm(justification.trim())
                } catch (caught) {
                  setError(getCompleteErrorMessage(caught, 'Suppression refusée.'))
                }
              }}
            >
              <Input
                required
                value={justification}
                onChange={(event) => setJustification(event.target.value)}
                placeholder="Justification"
                disabled={isPending}
              />
              {error ? (
                <p className="text-sm text-[var(--platform-status-problem-fg)]">{error}</p>
              ) : null}
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  className="h-10"
                  disabled={isPending}
                  onClick={() => setOpen(false)}
                >
                  Annuler
                </Button>
                <Button
                  type="submit"
                  variant="destructive"
                  className="h-10"
                  disabled={isPending || !justification.trim()}
                >
                  {isPending ? 'Suppression…' : confirmLabel}
                </Button>
              </div>
            </form>
          </PlatformDialog>
        </>
      ) : (
        <div data-testid="platform-delete-blocked">
          <p className="mt-1 text-sm text-[var(--platform-muted)]">Suppression impossible.</p>
          {blockingReasons.length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
              {blockingReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </section>
  )
}
