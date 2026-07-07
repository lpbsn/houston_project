import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'

type ActionPlanExecutionSkipSheetProps = {
  open: boolean
  isPending: boolean
  onConfirm: () => void
  onClose: () => void
}

export function ActionPlanExecutionSkipSheet({
  open,
  isPending,
  onConfirm,
  onClose,
}: ActionPlanExecutionSkipSheetProps) {
  return (
    <TerrainBottomSheet
      title="Passer la tâche"
      open={open}
      onClose={onClose}
      footer={
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="flex-1 rounded-lg"
            disabled={isPending}
            onClick={onConfirm}
          >
            Confirmer
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="flex-1 rounded-lg"
            disabled={isPending}
            onClick={onClose}
          >
            Annuler
          </Button>
        </div>
      }
    >
      <p className="text-sm text-[#555]">Cette tâche sera marquée comme passée.</p>
    </TerrainBottomSheet>
  )
}
