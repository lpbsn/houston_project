import { Button } from '@/components/ui/button'
import { TerrainStickyFooter } from '@/components/ui/terrain'

type ChecklistAssignmentCreateStickyFooterProps = {
  onClick: () => void
}

export function ChecklistAssignmentCreateStickyFooter({
  onClick,
}: ChecklistAssignmentCreateStickyFooterProps) {
  return (
    <TerrainStickyFooter>
      <Button
        type="button"
        className="h-11 w-full rounded-xl bg-[#1B4FD8]"
        onClick={onClick}
      >
        Nouvelle affectation
      </Button>
    </TerrainStickyFooter>
  )
}
