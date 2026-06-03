import { motion, useReducedMotion } from 'framer-motion'

import { TerrainCard, TerrainFieldLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { terrainTapProps } from '@/lib/terrain-motion'

import type { PermissionHints } from '../types'

const CANCEL_CONFIRM_MESSAGE =
  'Confirmer l’annulation de ce signal ? Cette action est définitive.'

type SignalLifecycleActionsProps = {
  hints: PermissionHints
  onCancel: () => void
  onResolve: () => void
  isPending: boolean
}

const outlineActionClassName =
  'inline-flex h-10 flex-1 shrink-0 items-center justify-center rounded-xl border border-[#E8E6DF] bg-background px-4 text-sm font-medium whitespace-nowrap outline-none select-none disabled:pointer-events-none disabled:opacity-50'

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
    variant: 'default' | 'destructive' = 'default',
  ) => {
    const destructiveClass =
      variant === 'destructive'
        ? 'border-[#E8E6DF] text-[#8B4513]'
        : 'border-[#E8E6DF]'

    if (shouldReduceMotion || isPending) {
      return (
        <Button
          key={key}
          type="button"
          variant="outline"
          className={`h-10 flex-1 rounded-xl text-sm ${destructiveClass}`}
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
        className={`${outlineActionClassName} ${destructiveClass}`}
        disabled={isPending}
        onClick={onClick}
        {...terrainTapProps(shouldReduceMotion)}
      >
        {label}
      </motion.button>
    )
  }

  return (
    <TerrainCard>
      <TerrainFieldLabel>Clôture du signal</TerrainFieldLabel>
      <div className="mt-2 flex flex-wrap gap-2">
        {hints.can_resolve
          ? renderActionButton('Résolu', onResolve, 'resolve')
          : null}
        {hints.can_cancel
          ? renderActionButton('Annuler', handleCancelClick, 'cancel', 'destructive')
          : null}
      </div>
    </TerrainCard>
  )
}
