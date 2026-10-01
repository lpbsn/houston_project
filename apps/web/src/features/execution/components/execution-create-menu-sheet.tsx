import { TerrainBottomSheet, TerrainDialog } from '@/components/ui/terrain'
import type { BootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'

import {
  getExecutionCreateMenuOptions,
  type ExecutionCreateMenuOptionId,
} from '../lib/execution-create-menu'

type ExecutionCreateMenuSheetProps = {
  open: boolean
  permissionHints: BootstrapPermissionHints | null | undefined
  presentation?: 'sheet' | 'dialog'
  onClose: () => void
  onSelectActionPlan: () => void
  onSelectCatalog: () => void
}

export function ExecutionCreateMenuSheet({
  open,
  permissionHints,
  presentation = 'sheet',
  onClose,
  onSelectActionPlan,
  onSelectCatalog,
}: ExecutionCreateMenuSheetProps) {
  const options = getExecutionCreateMenuOptions(permissionHints)

  function handleClose() {
    onClose()
  }

  function handleMainSelect(id: ExecutionCreateMenuOptionId) {
    if (id === 'action_plan') {
      onSelectActionPlan()
      handleClose()
      return
    }
    if (id === 'catalog') {
      onSelectCatalog()
      handleClose()
    }
  }

  const optionsList = (
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
                onClick={() => handleMainSelect(option.id)}
              >
                <span className="text-sm font-medium text-[#1a1a1a]">{option.label}</span>
              </button>
            </li>
          )
        })}
      </ul>
  )

  if (!open) {
    return null
  }

  if (presentation === 'dialog') {
    return (
      <TerrainDialog title="Créer" open={open} onClose={handleClose} testId="execution-create-menu-dialog">
        {optionsList}
      </TerrainDialog>
    )
  }

  return (
    <div data-testid="execution-create-menu-sheet">
      <TerrainBottomSheet title="Créer" open={open} onClose={handleClose}>
        {optionsList}
      </TerrainBottomSheet>
    </div>
  )
}
