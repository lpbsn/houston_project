import { Plus, Trash2 } from 'lucide-react'

import { TerrainBottomSheet, TerrainFieldLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ActionCreateAssigneeSection } from '@/features/actions/components/action-create-assignee-section'
import type { ScopedUserSearchResult } from '@/features/actions/types'

import {
  createActionPlanAssigneeDraft,
  type ActionPlanAssigneeDraft,
} from '../lib/action-plan-form-validation'

type ActionPlanAssigneeChronologySheetProps = {
  open: boolean
  establishmentId: string
  pilotBusinessUnitId: string
  assignees: ActionPlanAssigneeDraft[]
  useSharedChronology: boolean
  sharedStartAt: string
  sharedEndAt: string
  sharedVisibleFrom: string
  onAssigneesChange: (assignees: ActionPlanAssigneeDraft[]) => void
  onUseSharedChronologyChange: (value: boolean) => void
  onSharedStartAtChange: (value: string) => void
  onSharedEndAtChange: (value: string) => void
  onSharedVisibleFromChange: (value: string) => void
  onClose: () => void
  onConfirm: () => void
}

function toDatetimeLocalValue(isoValue: string): string {
  if (!isoValue.trim()) {
    return ''
  }
  const date = new Date(isoValue)
  if (Number.isNaN(date.getTime())) {
    return isoValue
  }
  const offset = date.getTimezoneOffset()
  const local = new Date(date.getTime() - offset * 60_000)
  return local.toISOString().slice(0, 16)
}

function fromDatetimeLocalValue(value: string): string {
  if (!value.trim()) {
    return ''
  }
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) {
    return value
  }
  return new Date(parsed).toISOString()
}

export function ActionPlanAssigneeChronologySheet({
  open,
  establishmentId,
  pilotBusinessUnitId,
  assignees,
  useSharedChronology,
  sharedStartAt,
  sharedEndAt,
  sharedVisibleFrom,
  onAssigneesChange,
  onUseSharedChronologyChange,
  onSharedStartAtChange,
  onSharedEndAtChange,
  onSharedVisibleFromChange,
  onClose,
  onConfirm,
}: ActionPlanAssigneeChronologySheetProps) {
  const selectedUsers: ScopedUserSearchResult[] = assignees
    .filter((assignee) => assignee.membershipId)
    .map((assignee) => ({
      id: assignee.membershipId,
      membership_id: assignee.membershipId,
      display_name: assignee.displayName,
      username: assignee.displayName,
      role: 'staff',
      email: null,
    }))

  function handleAssigneesChange(_ids: string[], users: ScopedUserSearchResult[]) {
    const next = users.map((user) => {
      const existing = assignees.find((assignee) => assignee.membershipId === user.membership_id)
      return (
        existing ??
        createActionPlanAssigneeDraft({
          membershipId: user.membership_id,
          businessUnitId: pilotBusinessUnitId,
          displayName: user.display_name,
        })
      )
    })
    onAssigneesChange(next)
  }

  function updateAssignee(id: string, patch: Partial<ActionPlanAssigneeDraft>) {
    onAssigneesChange(
      assignees.map((assignee) => (assignee.id === id ? { ...assignee, ...patch } : assignee)),
    )
  }

  return (
    <TerrainBottomSheet
      title="Assignés et chronologie"
      open={open}
      onClose={onClose}
      footer={
        <Button type="button" className="h-11 w-full rounded-xl" onClick={onConfirm}>
          Valider
        </Button>
      }
    >
      <div className="space-y-4">
        <ActionCreateAssigneeSection
          mode="multiple"
          establishmentId={establishmentId}
          businessUnitId={pilotBusinessUnitId || undefined}
          assigneeIds={assignees.map((assignee) => assignee.membershipId).filter(Boolean)}
          selectedUsers={selectedUsers}
          onAssigneesChange={handleAssigneesChange}
        />

        <label className="flex items-center gap-2 text-sm text-[#1a1a1a]">
          <input
            type="checkbox"
            checked={useSharedChronology}
            onChange={(event) => onUseSharedChronologyChange(event.target.checked)}
          />
          Chronologie commune
        </label>

        {useSharedChronology ? (
          <div className="space-y-3">
            <div>
              <TerrainFieldLabel>Début</TerrainFieldLabel>
              <Input
                type="datetime-local"
                value={toDatetimeLocalValue(sharedStartAt)}
                onChange={(event) => onSharedStartAtChange(fromDatetimeLocalValue(event.target.value))}
                className="h-10 border-[#E8E6DF] text-sm"
              />
            </div>
            <div>
              <TerrainFieldLabel>Fin</TerrainFieldLabel>
              <Input
                type="datetime-local"
                value={toDatetimeLocalValue(sharedEndAt)}
                onChange={(event) => onSharedEndAtChange(fromDatetimeLocalValue(event.target.value))}
                className="h-10 border-[#E8E6DF] text-sm"
              />
            </div>
            <div>
              <TerrainFieldLabel>Visible à partir de</TerrainFieldLabel>
              <Input
                type="datetime-local"
                value={toDatetimeLocalValue(sharedVisibleFrom)}
                onChange={(event) =>
                  onSharedVisibleFromChange(fromDatetimeLocalValue(event.target.value))
                }
                className="h-10 border-[#E8E6DF] text-sm"
              />
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {assignees.map((assignee) => (
              <div key={assignee.id} className="space-y-2 rounded-xl border border-[#E8E6DF] p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-[#1a1a1a]">
                    {assignee.displayName || 'Assigné'}
                  </p>
                  <button
                    type="button"
                    className="rounded-lg p-2 text-[#E24B4A]"
                    aria-label="Retirer l’assigné"
                    onClick={() =>
                      onAssigneesChange(assignees.filter((candidate) => candidate.id !== assignee.id))
                    }
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <Input
                  type="datetime-local"
                  value={toDatetimeLocalValue(assignee.startAt)}
                  onChange={(event) =>
                    updateAssignee(assignee.id, {
                      startAt: fromDatetimeLocalValue(event.target.value),
                    })
                  }
                  aria-label="Début"
                  className="h-10 border-[#E8E6DF] text-sm"
                />
                <Input
                  type="datetime-local"
                  value={toDatetimeLocalValue(assignee.endAt)}
                  onChange={(event) =>
                    updateAssignee(assignee.id, { endAt: fromDatetimeLocalValue(event.target.value) })
                  }
                  aria-label="Fin"
                  className="h-10 border-[#E8E6DF] text-sm"
                />
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              className="h-10 w-full rounded-xl border-dashed"
              onClick={() =>
                onAssigneesChange([
                  ...assignees,
                  createActionPlanAssigneeDraft({ businessUnitId: pilotBusinessUnitId }),
                ])
              }
            >
              <Plus className="mr-2 h-4 w-4" aria-hidden />
              Ajouter un créneau assigné
            </Button>
          </div>
        )}
      </div>
    </TerrainBottomSheet>
  )
}
