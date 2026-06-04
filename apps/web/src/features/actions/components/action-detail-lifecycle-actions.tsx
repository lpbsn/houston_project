import { Button } from '@/components/ui/button'

import type { ActionPermissionHints } from '../types'

type ActionDetailLifecycleActionsProps = {
  hints: ActionPermissionHints
  isPending: boolean
  onAccept: () => void
  onMarkDone: () => void
  onValidate: () => void
  onReopen: () => void
  onCancel: () => void
}

export function ActionDetailLifecycleActions({
  hints,
  isPending,
  onAccept,
  onMarkDone,
  onValidate,
  onReopen,
  onCancel,
}: ActionDetailLifecycleActionsProps) {
  const hasAnyAction =
    hints.can_accept ||
    hints.can_mark_done ||
    hints.can_validate ||
    hints.can_reopen ||
    hints.can_cancel

  if (!hasAnyAction) {
    return null
  }

  return (
    <div className="flex flex-col gap-2">
      {hints.can_accept ? (
        <Button className="w-full" disabled={isPending} onClick={onAccept}>
          Accepter
        </Button>
      ) : null}
      {hints.can_mark_done ? (
        <Button className="w-full" disabled={isPending} onClick={onMarkDone}>
          Marquer terminé
        </Button>
      ) : null}
      {hints.can_validate ? (
        <Button className="w-full" disabled={isPending} onClick={onValidate}>
          Valider
        </Button>
      ) : null}
      {hints.can_reopen ? (
        <Button className="w-full" variant="outline" disabled={isPending} onClick={onReopen}>
          Rouvrir
        </Button>
      ) : null}
      {hints.can_cancel ? (
        <Button
          className="w-full text-destructive"
          variant="outline"
          disabled={isPending}
          onClick={onCancel}
        >
          Annuler
        </Button>
      ) : null}
    </div>
  )
}
