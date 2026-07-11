import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'

const skipSheetButtonClassName =
  'flex-1 rounded-full border border-[#E8E6DF] bg-white font-semibold text-[#1a1a1a]'

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
            className={skipSheetButtonClassName}
            disabled={isPending}
            onClick={onConfirm}
          >
            Confirmer
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className={skipSheetButtonClassName}
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
