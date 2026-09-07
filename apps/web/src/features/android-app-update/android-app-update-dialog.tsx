import { Button } from '@/components/ui/button'

import {
  FORCE_UPDATE_MESSAGE,
  LATER_ACTION_LABEL,
  SOFT_UPDATE_MESSAGE,
  UPDATE_ACTION_LABEL,
} from './constants'

type AndroidAppUpdateDialogProps = {
  mode: 'flexible' | 'force'
  updateBusy?: boolean
  onUpdate: () => void
  onLater?: () => void
}

export function AndroidAppUpdateDialog({
  mode,
  updateBusy = false,
  onUpdate,
  onLater,
}: AndroidAppUpdateDialogProps) {
  const isForce = mode === 'force'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-6"
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="android-app-update-title"
        className="w-full max-w-sm rounded-2xl bg-background p-5 shadow-lg"
      >
        <p id="android-app-update-title" className="text-sm text-foreground">
          {isForce ? FORCE_UPDATE_MESSAGE : SOFT_UPDATE_MESSAGE}
        </p>
        <div className="mt-4 flex flex-col gap-2">
          <Button
            className="h-11 w-full rounded-xl"
            type="button"
            disabled={updateBusy}
            onClick={onUpdate}
          >
            {UPDATE_ACTION_LABEL}
          </Button>
          {isForce ? null : (
            <Button
              className="h-11 w-full rounded-xl"
              type="button"
              variant="outline"
              disabled={updateBusy}
              onClick={onLater}
            >
              {LATER_ACTION_LABEL}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
