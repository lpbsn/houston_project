import { TerrainStickyFooter } from '@/components/ui/terrain'

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
    <TerrainStickyFooter className="flex flex-col gap-2">
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
    </TerrainStickyFooter>
  )
}
