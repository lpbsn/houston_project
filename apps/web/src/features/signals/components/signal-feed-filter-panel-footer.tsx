import { Button } from '@/components/ui/button'

type SignalFeedFilterPanelFooterProps = {
  applyDisabled?: boolean
  selectAllDisabled?: boolean
  onApply: () => void
  onCancel: () => void
  onClearAll: () => void
  onSelectAll: () => void
}

export function SignalFeedFilterPanelFooter({
  applyDisabled = false,
  selectAllDisabled = false,
  onApply,
  onCancel,
  onClearAll,
  onSelectAll,
}: SignalFeedFilterPanelFooterProps) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <button
          type="button"
          className="text-[11px] font-semibold text-[#1B4FD8] disabled:opacity-50"
          disabled={selectAllDisabled}
          onClick={onSelectAll}
        >
          Tout sélectionner
        </button>
        <button
          type="button"
          className="text-[11px] font-semibold text-[#1B4FD8] disabled:opacity-50"
          disabled={selectAllDisabled}
          onClick={onClearAll}
        >
          Tout effacer
        </button>
      </div>
      <div className="flex gap-2">
        <Button type="button" variant="outline" className="flex-1" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="button" className="flex-1" onClick={onApply} disabled={applyDisabled}>
          Appliquer
        </Button>
      </div>
    </div>
  )
}
