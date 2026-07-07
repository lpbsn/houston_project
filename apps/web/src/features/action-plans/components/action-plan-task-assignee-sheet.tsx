import { AssigneeSection } from '@/components/domain/assignee-section'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import type { ScopedUserSearchResult } from '@/features/users/types'

type ActionPlanTaskAssigneeSheetProps = {
  open: boolean
  establishmentId: string
  businessUnitId: string
  assigneeMembershipId: string
  assigneeDisplayName: string
  onAssigneeChange: (membershipId: string, user: ScopedUserSearchResult) => void
  onClose: () => void
  onConfirm: () => void
}

export function ActionPlanTaskAssigneeSheet({
  open,
  establishmentId,
  businessUnitId,
  assigneeMembershipId,
  assigneeDisplayName,
  onAssigneeChange,
  onClose,
  onConfirm,
}: ActionPlanTaskAssigneeSheetProps) {
  if (!open) {
    return null
  }

  const selectedUser: ScopedUserSearchResult | null = assigneeMembershipId
    ? {
        id: assigneeMembershipId,
        membership_id: assigneeMembershipId,
        display_name: assigneeDisplayName,
        username: assigneeDisplayName,
        role: 'staff',
        email: null,
        business_unit_ids: [],
      }
    : null

  return (
    <TerrainBottomSheet
      title="Assigné"
      open
      onClose={onClose}
      footer={
        <Button type="button" className="h-11 w-full rounded-xl" onClick={onConfirm}>
          Valider
        </Button>
      }
    >
      <AssigneeSection
        mode="single"
        establishmentId={establishmentId}
        businessUnitId={businessUnitId || undefined}
        assignedTo={assigneeMembershipId}
        selectedUser={selectedUser}
        onAssignedToChange={onAssigneeChange}
      />
    </TerrainBottomSheet>
  )
}
