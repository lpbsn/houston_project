import { cn } from '@/lib/utils'

import type { ActionPermissionHints } from '../types'
import { ActionDetailProofDisabledSection } from './action-detail-disabled-section'
import { ActionDetailLifecycleActions } from './action-detail-lifecycle-actions'

type ActionDetailStickyFooterProps = {
  hints: ActionPermissionHints
  isPending: boolean
  mutationErrorMessage: string | null
  onAccept: () => void
  onMarkDone: () => void
  onValidate: () => void
  onReopen: () => void
  onCancel: () => void
}

export function ActionDetailStickyFooter({
  hints,
  isPending,
  mutationErrorMessage,
  onAccept,
  onMarkDone,
  onValidate,
  onReopen,
  onCancel,
}: ActionDetailStickyFooterProps) {
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
      <ActionDetailProofDisabledSection />

      <ActionDetailLifecycleActions
        hints={hints}
        isPending={isPending}
        onAccept={onAccept}
        onMarkDone={onMarkDone}
        onValidate={onValidate}
        onReopen={onReopen}
        onCancel={onCancel}
      />

      {mutationErrorMessage ? (
        <p className="px-1 text-sm text-destructive" role="alert">
          {mutationErrorMessage}
        </p>
      ) : null}
    </footer>
  )
}
