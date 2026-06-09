import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'

import {
  getChecklistCreateSubmenuOptions,
  getExecutionCreateMenuOptions,
  type ChecklistCreateSubmenuOptionId,
  type ExecutionCreateMenuOptionId,
} from '../lib/execution-create-menu'

type ExecutionCreateMenuSheetProps = {
  open: boolean
  role: string | null | undefined
  onClose: () => void
  onSelectAction: () => void
  onSelectFlashTodo: () => void
  onSelectChecklistCreate: () => void
  onSelectChecklistUse: () => void
}

type MenuView = 'main' | 'checklist'

export function ExecutionCreateMenuSheet({
  open,
  role,
  onClose,
  onSelectAction,
  onSelectFlashTodo,
  onSelectChecklistCreate,
  onSelectChecklistUse,
}: ExecutionCreateMenuSheetProps) {
  const [view, setView] = useState<MenuView>('main')

  const options =
    view === 'main' ? getExecutionCreateMenuOptions(role) : getChecklistCreateSubmenuOptions()
  const title = view === 'main' ? 'Créer' : 'Checklist'

  function handleClose() {
    setView('main')
    onClose()
  }

  function handleMainSelect(id: ExecutionCreateMenuOptionId) {
    if (id === 'action') {
      onSelectAction()
      handleClose()
      return
    }

    if (id === 'flash_todo') {
      onSelectFlashTodo()
      handleClose()
      return
    }

    if (id === 'checklist') {
      setView('checklist')
    }
  }

  function handleChecklistSelect(id: ChecklistCreateSubmenuOptionId) {
    if (id === 'create_registered') {
      onSelectChecklistCreate()
    } else {
      onSelectChecklistUse()
    }
    handleClose()
  }

  return (
    <TerrainBottomSheet title={title} open={open} onClose={handleClose}>
      {view === 'checklist' ? (
        <button
          type="button"
          className="mb-3 text-sm font-medium text-[#1B4FD8]"
          onClick={() => setView('main')}
        >
          Retour
        </button>
      ) : null}
      <ul className="flex flex-col gap-2">
        {options.map((option) => {
          if ('disabled' in option && option.disabled) {
            return (
              <li key={option.id}>
                <div
                  role="button"
                  aria-disabled="true"
                  className="flex min-h-11 cursor-not-allowed items-center justify-between rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 opacity-70"
                >
                  <span className="text-sm font-medium text-[#1a1a1a]">{option.label}</span>
                  {'badge' in option && option.badge ? (
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
                onClick={() =>
                  view === 'main'
                    ? handleMainSelect(option.id as ExecutionCreateMenuOptionId)
                    : handleChecklistSelect(option.id as ChecklistCreateSubmenuOptionId)
                }
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
