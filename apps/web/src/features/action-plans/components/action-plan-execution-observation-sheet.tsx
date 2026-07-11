import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ActionPlanExecutionObservationSheetProps = {
  open: boolean
  text: string
  isPending: boolean
  onTextChange: (value: string) => void
  onConfirm: () => void
  onClose: () => void
}

export function ActionPlanExecutionObservationSheet({
  open,
  text,
  isPending,
  onTextChange,
  onConfirm,
  onClose,
}: ActionPlanExecutionObservationSheetProps) {
  return (
    <TerrainBottomSheet
      title="Créer une observation"
      open={open}
      onClose={onClose}
      footer={
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            className={cn(
              'flex-1 rounded-lg text-white',
              terrainBrandAction.bg,
              terrainBrandAction.hover,
            )}
            disabled={isPending || !text.trim()}
            onClick={onConfirm}
          >
            Envoyer
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
      <Textarea
        value={text}
        onChange={(event) => onTextChange(event.target.value)}
        placeholder="Décrivez l’observation..."
        className="min-h-28 border-[#E8E6DF]"
      />
    </TerrainBottomSheet>
  )
}
