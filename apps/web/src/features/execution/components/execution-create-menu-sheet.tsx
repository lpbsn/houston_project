import { TerrainBottomSheet } from '@/components/ui/terrain'

import {
  getExecutionCreateMenuOptions,
  type ExecutionCreateMenuOptionId,
} from '../lib/execution-create-menu'

type ExecutionCreateMenuSheetProps = {
  open: boolean
  role: string | null | undefined
  onClose: () => void
  onSelectAction: () => void
  onSelectPersonalChecklist: () => void
}

export function ExecutionCreateMenuSheet({
  open,
  role,
  onClose,
  onSelectAction,
  onSelectPersonalChecklist,
}: ExecutionCreateMenuSheetProps) {
  const options = getExecutionCreateMenuOptions(role)

  function handleSelect(id: ExecutionCreateMenuOptionId) {
    if (id === 'action') {
      onSelectAction()
      onClose()
      return
    }

    if (id === 'personal_checklist') {
      onSelectPersonalChecklist()
      onClose()
    }
  }

  return (
    <TerrainBottomSheet title="Créer" open={open} onClose={onClose}>
      <ul className="flex flex-col gap-2">
        {options.map((option) => {
          if (option.disabled) {
            return (
              <li key={option.id}>
                <div
                  role="button"
                  aria-disabled="true"
                  className="flex min-h-11 cursor-not-allowed items-center justify-between rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 opacity-70"
                >
                  <span className="text-sm font-medium text-[#1a1a1a]">{option.label}</span>
                  {option.badge ? (
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-[#7D7B75]">
                      {option.badge}
                    </span>
                  ) : null}
                </div>
              </li>
            )
          }

          return (
            <li key={option.id}>
              <button
                type="button"
                className="flex min-h-11 w-full items-center justify-between rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 text-left"
                onClick={() => handleSelect(option.id)}
              >
                <span className="text-sm font-medium text-[#1a1a1a]">{option.label}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </TerrainBottomSheet>
  )
}
