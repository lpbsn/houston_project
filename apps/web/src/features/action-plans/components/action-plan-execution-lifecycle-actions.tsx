import { motion, useReducedMotion } from 'framer-motion'

import { Button } from '@/components/ui/button'
import { terrain } from '@/lib/terrain-styles'
import { terrainTapProps } from '@/lib/terrain-motion'
import { cn } from '@/lib/utils'

import type { ActionPlanExecutionPermissionHints } from '../types'
import {
  canShowActionPlanExecutionCancel,
  canShowActionPlanExecutionMarkDone,
  canShowActionPlanExecutionReopen,
  canShowActionPlanExecutionValidate,
} from '../lib/action-plan-permission-hints'

type ActionPlanExecutionLifecycleActionsProps = {
  hints: ActionPlanExecutionPermissionHints
  isTerminal: boolean
  isPending: boolean
  onMarkDone: () => void
  onValidate: () => void
  onReopen: () => void
  onCancel: () => void
}

type LifecycleTone = 'success' | 'danger' | 'primary'

const lifecycleActionClassName =
  'inline-flex h-10 flex-1 items-center justify-center rounded-2xl px-3 text-[14px] font-semibold text-white outline-none select-none disabled:pointer-events-none disabled:opacity-50'

function lifecycleToneClassName(tone: LifecycleTone): string {
  if (tone === 'success') {
    return terrain.successBg
  }
  if (tone === 'danger') {
    return terrain.dangerBg
  }
  return terrain.primaryBg
}

export function ActionPlanExecutionLifecycleActions({
  hints,
  isTerminal,
  isPending,
  onMarkDone,
  onValidate,
  onReopen,
  onCancel,
}: ActionPlanExecutionLifecycleActionsProps) {
  const shouldReduceMotion = useReducedMotion()

  const buttons: Array<{ key: string; label: string; onClick: () => void; tone: LifecycleTone }> =
    []

  if (canShowActionPlanExecutionMarkDone(hints)) {
    buttons.push({
      key: 'mark-done',
      label: 'Marquer terminé',
      onClick: onMarkDone,
      tone: 'success',
    })
  }
  if (canShowActionPlanExecutionValidate(hints)) {
    buttons.push({ key: 'validate', label: 'Valider', onClick: onValidate, tone: 'success' })
  }
  if (canShowActionPlanExecutionReopen(hints)) {
    buttons.push({ key: 'reopen', label: 'Rouvrir', onClick: onReopen, tone: 'primary' })
  }
  if (canShowActionPlanExecutionCancel(hints, { isTerminal })) {
    buttons.push({ key: 'cancel', label: 'Annuler', onClick: onCancel, tone: 'danger' })
  }

  if (buttons.length === 0) {
    return null
  }

  const renderActionButton = (
    label: string,
    onClick: () => void,
    key: string,
    tone: LifecycleTone,
  ) => {
    const toneClass = lifecycleToneClassName(tone)

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
      {buttons.map(({ key, label, onClick, tone }) =>
        renderActionButton(label, onClick, key, tone),
      )}
    </div>
  )
}
