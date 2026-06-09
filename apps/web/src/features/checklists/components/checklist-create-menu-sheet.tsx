import { TerrainBottomSheet } from '@/components/ui/terrain'

import {
  getChecklistCreateMenuOptions,
  type ChecklistCreateMenuOptionId,
} from '../lib/checklist-create-menu'

type ChecklistCreateMenuSheetProps = {
  open: boolean
  role: string | null | undefined
  onClose: () => void
  onSelectShared: () => void
  onSelectPersonal: () => void
}

export function ChecklistCreateMenuSheet({
  open,
  role,
  onClose,
  onSelectShared,
  onSelectPersonal,
}: ChecklistCreateMenuSheetProps) {
  const options = getChecklistCreateMenuOptions(role)

  function handleSelect(id: ChecklistCreateMenuOptionId) {
    if (id === 'shared') {
      onSelectShared()
      onClose()
      return
    }

    if (id === 'personal') {
      onSelectPersonal()
      onClose()
    }
  }

  return (
    <TerrainBottomSheet title="Créer une checklist" open={open} onClose={onClose}>
      <ul className="flex flex-col gap-2">
        {options.map((option) => (
          <li key={option.id}>
            <button
              type="button"
              className="flex min-h-11 w-full items-center justify-between rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 text-left"
              onClick={() => handleSelect(option.id)}
            >
              <span className="text-sm font-medium text-[#1a1a1a]">{option.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </TerrainBottomSheet>
  )
}
