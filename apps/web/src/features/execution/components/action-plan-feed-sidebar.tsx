import type { ReactNode } from 'react'
import { Check, X } from 'lucide-react'

import type { ActionPlanFeedSidebarState } from '@/features/execution/lib/action-plan-execution-feed-card-display'
import {
  actionPlanFeedOverdueBgClassName,
  actionPlanFeedScheduledBgClassName,
  actionPlanFeedTealBgClassName,
  terrain,
} from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ActionPlanFeedSidebarProps = {
  state?: ActionPlanFeedSidebarState
  variant?: 'done' | 'canceled'
  validatedAt?: string | null
  className?: string
}

function getSidebarAriaLabel(state: ActionPlanFeedSidebarState): string {
  switch (state.variant) {
    case 'countdown':
      return `Échéance dans ${state.value}`
    case 'start_countdown':
      return `Début dans ${state.value}`
    case 'no_deadline':
      return 'Sans échéance'
    case 'no_start':
      return 'Sans date de début'
    case 'overdue':
      return `Échéance dépassée de ${state.value}`
  }
}

function getSidebarBackgroundClassName(state: ActionPlanFeedSidebarState): string {
  if (state.variant === 'overdue') {
    return actionPlanFeedOverdueBgClassName
  }
  if (state.variant === 'start_countdown' || state.variant === 'no_start') {
    return actionPlanFeedScheduledBgClassName
  }
  return actionPlanFeedTealBgClassName
}

function SidebarIconCircle({ children }: { children: ReactNode }) {
  return (
    <div
      className="flex h-8 w-8 items-center justify-center rounded-full bg-white/20"
      aria-hidden
    >
      {children}
    </div>
  )
}

function TerminalSidebarIcon({ variant }: { variant: 'done' | 'canceled' }) {
  const Icon = variant === 'done' ? Check : X

  return (
    <SidebarIconCircle>
      <Icon className="h-4 w-4 shrink-0" strokeWidth={2.5} />
    </SidebarIconCircle>
  )
}

export function ActionPlanFeedSidebar({
  state,
  variant,
  validatedAt = null,
  className,
}: ActionPlanFeedSidebarProps) {
  if (variant === 'done' || variant === 'canceled') {
    const backgroundClassName =
      variant === 'done' ? terrain.successBg : 'bg-[#7D7B75]'
    const ariaLabel =
      variant === 'canceled' ? 'Annulé' : validatedAt != null ? 'Validée' : 'Terminé'

    return (
      <div
        className={cn(
          'flex w-[60px] shrink-0 flex-col items-center justify-center self-stretch text-white',
          backgroundClassName,
          className,
        )}
        aria-label={ariaLabel}
      >
        <TerminalSidebarIcon variant={variant} />
      </div>
    )
  }

  if (!state) {
    return null
  }

  return (
    <div
      className={cn(
        'flex w-[60px] shrink-0 flex-col items-center justify-center self-stretch text-white',
        getSidebarBackgroundClassName(state),
        className,
      )}
      aria-label={getSidebarAriaLabel(state)}
    >
      {state.variant === 'countdown' ||
      state.variant === 'overdue' ||
      state.variant === 'start_countdown' ? (
        <>
          <span className="text-[10px] font-medium uppercase leading-none tracking-wide">
            {state.prefix}
          </span>
          <span className="mt-0.5 text-xl font-bold leading-none tabular-nums">{state.value}</span>
        </>
      ) : null}
      {state.variant === 'no_deadline' || state.variant === 'no_start' ? (
        <SidebarIconCircle>
          <span className="text-lg font-bold leading-none">∞</span>
        </SidebarIconCircle>
      ) : null}
    </div>
  )
}
