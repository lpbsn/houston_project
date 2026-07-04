import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'

import { buildActionPlanUseRequest } from '../lib/action-plan-create-payload'
import type { ActionPlanAssigneeDraft } from '../lib/action-plan-form-validation'
import { ActionPlanAssigneeChronologySheet } from './action-plan-assignee-chronology-sheet'

type ActionPlanUseSheetProps = {
  open: boolean
  establishmentId: string
  pilotBusinessUnitId: string
  isPending: boolean
  onClose: () => void
  onConfirm: (body: ReturnType<typeof buildActionPlanUseRequest>) => void
}

export function ActionPlanUseSheet({
  open,
  establishmentId,
  pilotBusinessUnitId,
  isPending,
  onClose,
  onConfirm,
}: ActionPlanUseSheetProps) {
  const [assigneeSheetOpen, setAssigneeSheetOpen] = useState(false)
  const [assignees, setAssignees] = useState<ActionPlanAssigneeDraft[]>([])
  const [useSharedChronology, setUseSharedChronology] = useState(true)
  const [sharedStartAt, setSharedStartAt] = useState('')
  const [sharedEndAt, setSharedEndAt] = useState('')
  const [sharedVisibleFrom, setSharedVisibleFrom] = useState('')

  function handleOpenAssignees() {
    setAssigneeSheetOpen(true)
  }

  function handleConfirmUse() {
    onConfirm(
      buildActionPlanUseRequest({
        assignees,
        useSharedChronology,
        sharedStartAt,
        sharedEndAt,
        sharedVisibleFrom,
      }),
    )
  }

  return (
    <>
      <TerrainBottomSheet
        title="Utiliser ce plan"
        open={open && !assigneeSheetOpen}
        onClose={onClose}
        footer={
          <div className="flex flex-col gap-2">
            <Button
              type="button"
              variant="outline"
              className="h-11 w-full rounded-xl"
              onClick={handleOpenAssignees}
            >
              Configurer assignés et chronologie
            </Button>
            <Button
              type="button"
              className="h-11 w-full rounded-xl"
              disabled={isPending}
              onClick={handleConfirmUse}
            >
              Lancer l&apos;exécution
            </Button>
          </div>
        }
      >
        <p className="text-sm text-[#7D7B75]">
          {assignees.length > 0
            ? `${assignees.length} assigné(s) configuré(s).`
            : 'Aucun assigné — vous pouvez lancer sans assigné ou en ajouter.'}
        </p>
      </TerrainBottomSheet>

      <ActionPlanAssigneeChronologySheet
        open={open && assigneeSheetOpen}
        establishmentId={establishmentId}
        pilotBusinessUnitId={pilotBusinessUnitId}
        assignees={assignees}
        useSharedChronology={useSharedChronology}
        sharedStartAt={sharedStartAt}
        sharedEndAt={sharedEndAt}
        sharedVisibleFrom={sharedVisibleFrom}
        onAssigneesChange={setAssignees}
        onUseSharedChronologyChange={setUseSharedChronology}
        onSharedStartAtChange={setSharedStartAt}
        onSharedEndAtChange={setSharedEndAt}
        onSharedVisibleFromChange={setSharedVisibleFrom}
        onClose={() => setAssigneeSheetOpen(false)}
        onConfirm={() => setAssigneeSheetOpen(false)}
      />
    </>
  )
}
