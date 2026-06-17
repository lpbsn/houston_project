import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { ActionCreateAssigneeSection } from '@/features/actions/components/action-create-assignee-section'
import { ActionCreateSheetFooter } from '@/features/actions/components/action-create-sheet-footer'
import type { ScopedUserSearchResult } from '@/features/actions/types'

type ChecklistAssigneeSheetProps = {
  establishmentId: string
  businessUnitId: string
  assignedTo: string
  selectedUser: ScopedUserSearchResult | null
  onClose: () => void
  onApply: (membershipId: string, user: ScopedUserSearchResult) => void
}

export function ChecklistAssigneeSheet({
  establishmentId,
  businessUnitId,
  assignedTo,
  selectedUser,
  onClose,
  onApply,
}: ChecklistAssigneeSheetProps) {
  const [draftAssignedTo, setDraftAssignedTo] = useState(assignedTo)
  const [draftSelectedUser, setDraftSelectedUser] = useState(selectedUser)

  function handleApply() {
    if (!draftAssignedTo || !draftSelectedUser) {
      return
    }
    onApply(draftAssignedTo, draftSelectedUser)
    onClose()
  }

  return (
    <TerrainBottomSheet
      title="Attribuer à"
      open
      onClose={onClose}
      footer={
        <ActionCreateSheetFooter
          applyDisabled={!draftAssignedTo}
          onCancel={onClose}
          onApply={handleApply}
        />
      }
    >
      <ActionCreateAssigneeSection
        establishmentId={establishmentId}
        businessUnitId={businessUnitId}
        assignedTo={draftAssignedTo}
        selectedUser={draftSelectedUser}
        onAssignedToChange={(membershipId, user) => {
          setDraftAssignedTo(membershipId)
          setDraftSelectedUser(user)
        }}
      />
    </TerrainBottomSheet>
  )
}
