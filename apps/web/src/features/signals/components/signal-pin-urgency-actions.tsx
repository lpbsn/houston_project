import { Button } from '@/components/ui/button'

import type { PermissionHints } from '../types'

type SignalPinUrgencyActionsProps = {
  hints: PermissionHints
  isPinned: boolean
  urgency: string
  onPin: () => void
  onUnpin: () => void
  onSetUrgency: (urgency: 'normal' | 'high') => void
  isPending: boolean
}

export function SignalPinUrgencyActions({
  hints,
  isPinned,
  urgency,
  onPin,
  onUnpin,
  onSetUrgency,
  isPending,
}: SignalPinUrgencyActionsProps) {
  if (!hints.can_pin && !hints.can_set_urgency) {
    return null
  }

  return (
    <div className="flex flex-wrap gap-2">
      {hints.can_pin ? (
        <Button
          type="button"
          variant="outline"
          className="rounded-xl border-[#e7dfd1]"
          disabled={isPending}
          onClick={isPinned ? onUnpin : onPin}
        >
          {isPinned ? 'Désépingler' : 'Épingler'}
        </Button>
      ) : null}
      {hints.can_set_urgency ? (
        <Button
          type="button"
          variant="outline"
          className="rounded-xl border-[#e7dfd1]"
          disabled={isPending}
          onClick={() => onSetUrgency(urgency === 'high' ? 'normal' : 'high')}
        >
          {urgency === 'high' ? 'Priorité normale' : 'Marquer urgent'}
        </Button>
      ) : null}
    </div>
  )
}
