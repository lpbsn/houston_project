import { AssigneeSection } from '@/components/domain/assignee-section'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import type { ScopedUserSearchResult } from '@/features/users/types'

import {
  createActionPlanAssigneeDraft,
  type ActionPlanAssigneeDraft,
} from '../lib/action-plan-form-validation'

type ActionPlanAssigneesSheetProps = {
  open: boolean
  establishmentId: string
  pilotBusinessUnitId: string
  assignees: ActionPlanAssigneeDraft[]
  onAssigneesChange: (assignees: ActionPlanAssigneeDraft[]) => void
  onClose: () => void
  onConfirm: () => void
}

export function ActionPlanAssigneesSheet({
  open,
  establishmentId,
  pilotBusinessUnitId,
  assignees,
  onAssigneesChange,
  onClose,
  onConfirm,
}: ActionPlanAssigneesSheetProps) {
  const selectedUsers: ScopedUserSearchResult[] = assignees
    .filter((assignee) => assignee.membershipId)
    .map((assignee) => ({
      id: assignee.membershipId,
      membership_id: assignee.membershipId,
      display_name: assignee.displayName,
      username: assignee.displayName,
      role: 'staff',
      email: null,
      business_unit_ids: assignee.businessUnitId ? [assignee.businessUnitId] : [],
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

  return (
    <TerrainBottomSheet
      title="Assignés"
      open={open}
      onClose={onClose}
      footer={
        <Button type="button" className="h-11 w-full rounded-xl" onClick={onConfirm}>
          Valider
        </Button>
      }
    >
      <AssigneeSection
        mode="multiple"
        establishmentId={establishmentId}
        businessUnitId={pilotBusinessUnitId || undefined}
        assigneeIds={assignees.map((assignee) => assignee.membershipId).filter(Boolean)}
        selectedUsers={selectedUsers}
        onAssigneesChange={handleAssigneesChange}
      />
    </TerrainBottomSheet>
  )
}
