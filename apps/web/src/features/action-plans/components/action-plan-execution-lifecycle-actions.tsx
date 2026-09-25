import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import {
  actionPlanExecutionDetailCancelBgClassName,
  actionPlanExecutionDetailLifecycleButtonClassName,
  actionPlanExecutionDetailMarkDoneBgClassName,
  actionPlanExecutionDetailReopenBgClassName,
  actionPlanExecutionDetailValidateBgClassName,
} from '@/lib/terrain-styles'
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
  layout?: 'touch' | 'page'
  onMarkDone: () => void
  onValidate: () => void
  onReopen: () => void
  onCancel: () => void
}

type LifecycleTone = 'markDone' | 'validate' | 'reopen' | 'cancel'

const lifecycleToneClassNames: Record<LifecycleTone, string> = {
  markDone: actionPlanExecutionDetailMarkDoneBgClassName,
  validate: actionPlanExecutionDetailValidateBgClassName,
  reopen: actionPlanExecutionDetailReopenBgClassName,
  cancel: actionPlanExecutionDetailCancelBgClassName,
}

function getLifecycleButtonClassName(tone: LifecycleTone): string {
  return cn(actionPlanExecutionDetailLifecycleButtonClassName, lifecycleToneClassNames[tone])
}

function renderMarkDoneLabel() {
  return (
    <span className="flex flex-col leading-tight">
      <span>Marquer</span>
      <span>terminé</span>
    </span>
  )
}

export function ActionPlanExecutionLifecycleActions({
  hints,
  isTerminal,
  isPending,
  layout = 'touch',
  onMarkDone,
  onValidate,
  onReopen,
  onCancel,
}: ActionPlanExecutionLifecycleActionsProps) {
  const shouldReduceMotion = useReducedMotion()

  const buttons: Array<{
    key: string
    label: string
    ariaLabel?: string
    content: ReactNode
    onClick: () => void
    tone: LifecycleTone
  }> = []

  if (canShowActionPlanExecutionMarkDone(hints)) {
    buttons.push({
      key: 'mark-done',
      label: 'Marquer terminé',
      ariaLabel: 'Marquer terminé',
      content: layout === 'page' ? 'Marquer terminé' : renderMarkDoneLabel(),
      onClick: onMarkDone,
      tone: 'markDone',
    })
  }
  if (canShowActionPlanExecutionValidate(hints)) {
    buttons.push({
      key: 'validate',
      label: 'Valider',
      content: 'Valider',
      onClick: onValidate,
      tone: 'validate',
    })
  }
  if (canShowActionPlanExecutionReopen(hints)) {
    buttons.push({
      key: 'reopen',
      label: 'Rouvrir',
      content: 'Rouvrir',
      onClick: onReopen,
      tone: 'reopen',
    })
  }
  if (canShowActionPlanExecutionCancel(hints, { isTerminal })) {
    buttons.push({
      key: 'cancel',
      label: 'Annuler',
      content: 'Annuler',
      onClick: onCancel,
      tone: 'cancel',
    })
  }

  if (buttons.length === 0) {
    return null
  }

  const renderActionButton = (
    content: ReactNode,
    onClick: () => void,
    key: string,
    tone: LifecycleTone,
    ariaLabel?: string,
  ) => {
    const isSecondaryPageAction = layout === 'page' && (tone === 'reopen' || tone === 'cancel')
    const className = cn(
      getLifecycleButtonClassName(tone),
      layout === 'page' && 'h-9 min-h-9 flex-none rounded-lg px-3 text-sm',
      isSecondaryPageAction &&
        'bg-transparent text-[#5F5A52] hover:bg-[#F5F4F0] hover:text-[#1a1a1a]',
    )

    if (shouldReduceMotion || isPending) {
      return (
        <Button
          key={key}
          type="button"
          className={className}
          disabled={isPending}
          aria-label={ariaLabel}
          onClick={onClick}
        >
          {content}
        </Button>
      )
    }

    return (
      <motion.button
        key={key}
        type="button"
        className={className}
        disabled={isPending}
        aria-label={ariaLabel}
        onClick={onClick}
        {...terrainTapProps(shouldReduceMotion)}
      >
        {content}
      </motion.button>
    )
  }

  return (
    <div className={layout === 'page' ? 'flex flex-wrap justify-end gap-2' : 'flex w-full gap-2'}>
      {buttons.map(({ key, content, onClick, tone, ariaLabel }) =>
        renderActionButton(content, onClick, key, tone, ariaLabel),
      )}
    </div>
  )
}
