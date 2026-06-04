import { Button } from '@/components/ui/button'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import type { PermissionHints } from '../types'
import { SignalLifecycleActions } from './signal-lifecycle-actions'

type SignalDetailStickyFooterProps = {
  hints: PermissionHints
  isPending: boolean
  showCreateActionPlan: boolean
  onResolve: () => void
  onCancel: () => void
  onCreateActionPlan: () => void
  lifecycleErrorMessage?: string | null
}

export function SignalDetailStickyFooter({
  hints,
  isPending,
  showCreateActionPlan,
  onResolve,
  onCancel,
  onCreateActionPlan,
  lifecycleErrorMessage,
}: SignalDetailStickyFooterProps) {
  const hasLifecycle = hints.can_resolve || hints.can_cancel

  return (
    <footer
      className={cn(
        'sticky bottom-0 z-10 mt-auto shrink-0',
        'border-t border-[#E8E6DF] bg-[#F5F4F0]',
        'shadow-[0_-4px_12px_rgba(0,0,0,0.04)]',
        'px-3 pt-2.5 pb-[max(0.75rem,env(safe-area-inset-bottom))]',
        'flex flex-col gap-2',
      )}
    >
      {hasLifecycle ? (
        <SignalLifecycleActions
          hints={hints}
          isPending={isPending}
          onCancel={onCancel}
          onResolve={onResolve}
        />
      ) : null}

      {showCreateActionPlan ? (
        <Button
          type="button"
          className={cn(
            'h-11 w-full rounded-2xl text-[15px] font-semibold text-white hover:bg-[#1B4FD8]/95',
            terrain.primaryBg,
          )}
          onClick={onCreateActionPlan}
        >
          + Plan d&apos;action
        </Button>
      ) : null}

      {lifecycleErrorMessage ? (
        <p className="px-1 text-sm text-destructive" role="alert">
          {lifecycleErrorMessage}
        </p>
      ) : null}
    </footer>
  )
}
