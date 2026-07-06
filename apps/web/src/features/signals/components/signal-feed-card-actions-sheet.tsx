import { createPortal } from 'react-dom'

import { TerrainBottomSheet } from '@/components/ui/terrain'

import {
  getSignalFeedCardActionOptions,
  type SignalFeedCardActionId,
} from '../lib/signal-feed-card-actions'
import type { SignalFeedItem } from '../types'

type SignalFeedCardActionsSheetProps = {
  item: SignalFeedItem
  open: boolean
  isPending: boolean
  onClose: () => void
  onSelectAction: (actionId: SignalFeedCardActionId) => void
}

export function SignalFeedCardActionsSheet({
  item,
  open,
  isPending,
  onClose,
  onSelectAction,
}: SignalFeedCardActionsSheetProps) {
  const options = getSignalFeedCardActionOptions(item)

  function handleClose() {
    onClose()
  }

  function handleSelect(actionId: SignalFeedCardActionId, event: { stopPropagation: () => void }) {
    event.stopPropagation()
    if (isPending) {
      return
    }
    onSelectAction(actionId)
    handleClose()
  }

  return createPortal(
    <div onClick={(event) => event.stopPropagation()}>
      <TerrainBottomSheet title="Actions" open={open} onClose={handleClose}>
        <ul className="flex flex-col gap-2">
          {options.map((option) => (
            <li key={option.id}>
              <button
                type="button"
                className="flex min-h-11 w-full items-center justify-between rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 text-left disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isPending}
                onClick={(event) => handleSelect(option.id, event)}
              >
                <span className="text-sm font-medium text-[#1a1a1a]">{option.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </TerrainBottomSheet>
    </div>,
    document.body,
  )
}
