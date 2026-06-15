import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

type ChecklistExecutionSkipSheetProps = {
  open: boolean
  skipReason: string
  isPending: boolean
  onSkipReasonChange: (value: string) => void
  onConfirm: () => void
  onClose: () => void
}

export function ChecklistExecutionSkipSheet({
  open,
  skipReason,
  isPending,
  onSkipReasonChange,
  onConfirm,
  onClose,
}: ChecklistExecutionSkipSheetProps) {
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
      <Input
        value={skipReason}
        onChange={(event) => onSkipReasonChange(event.target.value)}
        placeholder="Raison (optionnel)"
        className="h-10 border-[#E8E6DF] text-sm"
      />
    </TerrainBottomSheet>
  )
}
