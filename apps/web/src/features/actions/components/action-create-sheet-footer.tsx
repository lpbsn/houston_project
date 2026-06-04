import { Button } from '@/components/ui/button'

type ActionCreateSheetFooterProps = {
  applyDisabled?: boolean
  onApply: () => void
  onCancel: () => void
}

export function ActionCreateSheetFooter({
  applyDisabled = false,
  onApply,
  onCancel,
}: ActionCreateSheetFooterProps) {
  return (
    <div className="flex gap-2">
      <Button type="button" variant="outline" className="flex-1" onClick={onCancel}>
        Annuler
      </Button>
      <Button type="button" className="flex-1" onClick={onApply} disabled={applyDisabled}>
        Appliquer
      </Button>
    </div>
  )
}
