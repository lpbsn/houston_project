import { useEffect } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
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

  useEffect(() => {
    if (!open || presentation !== 'dialog') {
      return
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, open, presentation])

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
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="execution-create-menu-title"
          data-testid="execution-create-menu-dialog"
          className="w-full max-w-sm rounded-xl border border-[#E8E6DF] bg-white p-4 shadow-lg"
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 id="execution-create-menu-title" className="text-sm font-semibold text-[#1a1a1a]">
              Créer
            </h2>
            <button
              type="button"
              className="rounded-md px-2 py-1 text-sm font-medium text-[#5c564e] hover:bg-[#F5F4F0]"
              onClick={handleClose}
            >
              Fermer
            </button>
          </div>
          {optionsList}
        </div>
      </div>
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
