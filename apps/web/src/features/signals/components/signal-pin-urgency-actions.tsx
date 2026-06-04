import { motion, useReducedMotion } from 'framer-motion'

import { Button } from '@/components/ui/button'
import { terrainTapProps } from '@/lib/terrain-motion'

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

const outlineActionClassName =
  'inline-flex h-7 shrink-0 items-center justify-center rounded-[10px] border border-[#E8E6DF] bg-background px-2 text-[11px] font-medium whitespace-nowrap text-[#555] outline-none select-none disabled:pointer-events-none disabled:opacity-50'

export function SignalPinUrgencyActions({
  hints,
  isPinned,
  urgency,
  onPin,
  onUnpin,
  onSetUrgency,
  isPending,
}: SignalPinUrgencyActionsProps) {
  const shouldReduceMotion = useReducedMotion()

  if (!hints.can_pin && !hints.can_set_urgency) {
    return null
  }

  const renderActionButton = (
    label: string,
    onClick: () => void,
    key: string,
  ) => {
    if (shouldReduceMotion || isPending) {
      return (
        <Button
          key={key}
          type="button"
          variant="outline"
          className="h-7 rounded-[10px] border-[#E8E6DF] px-2 text-[11px] font-medium text-[#555]"
          disabled={isPending}
          onClick={onClick}
        >
          {label}
        </Button>
      )
    }

    return (
      <motion.button
        key={key}
        type="button"
        className={outlineActionClassName}
        disabled={isPending}
        onClick={onClick}
        {...terrainTapProps(shouldReduceMotion)}
      >
        {label}
      </motion.button>
    )
  }

  return (
    <div className="flex flex-wrap gap-1.5 px-0.5">
      {hints.can_pin
        ? renderActionButton(
            isPinned ? 'Désépingler' : 'Épingler',
            isPinned ? onUnpin : onPin,
            'pin',
          )
        : null}
      {hints.can_set_urgency
        ? renderActionButton(
            urgency === 'high' ? 'Priorité normale' : 'Marquer urgent',
            () => onSetUrgency(urgency === 'high' ? 'normal' : 'high'),
            'urgency',
          )
        : null}
    </div>
  )
}
