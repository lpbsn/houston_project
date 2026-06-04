import { motion, useReducedMotion } from 'framer-motion'

import { Button } from '@/components/ui/button'
import { terrain } from '@/lib/terrain-styles'
import { terrainTapProps } from '@/lib/terrain-motion'
import { cn } from '@/lib/utils'

import type { PermissionHints } from '../types'

const CANCEL_CONFIRM_MESSAGE =
  'Confirmer l’annulation de ce signal ? Cette action est définitive.'

type SignalLifecycleActionsProps = {
  hints: PermissionHints
  onCancel: () => void
  onResolve: () => void
  isPending: boolean
}

const lifecycleActionClassName =
  'inline-flex h-10 flex-1 items-center justify-center rounded-2xl px-3 text-[14px] font-semibold text-white outline-none select-none disabled:pointer-events-none disabled:opacity-50'

export function SignalLifecycleActions({
  hints,
  onCancel,
  onResolve,
  isPending,
}: SignalLifecycleActionsProps) {
  const shouldReduceMotion = useReducedMotion()

  if (!hints.can_cancel && !hints.can_resolve) {
    return null
  }

  const handleCancelClick = () => {
    if (!window.confirm(CANCEL_CONFIRM_MESSAGE)) {
      return
    }
    onCancel()
  }

  const renderActionButton = (
    label: string,
    onClick: () => void,
    key: string,
    tone: 'success' | 'danger',
  ) => {
    const toneClass = tone === 'success' ? terrain.successBg : terrain.dangerBg

    if (shouldReduceMotion || isPending) {
      return (
        <Button
          key={key}
          type="button"
          className={cn('h-10 flex-1 rounded-2xl text-[14px] font-semibold text-white', toneClass)}
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
        className={cn(lifecycleActionClassName, toneClass)}
        disabled={isPending}
        onClick={onClick}
        {...terrainTapProps(shouldReduceMotion)}
      >
        {label}
      </motion.button>
    )
  }

  return (
    <div className="flex w-full gap-2">
      {hints.can_resolve
        ? renderActionButton('Résolu', onResolve, 'resolve', 'success')
        : null}
      {hints.can_cancel
        ? renderActionButton('Annuler', handleCancelClick, 'cancel', 'danger')
        : null}
    </div>
  )
}
