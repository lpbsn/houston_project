import type { SignalViewMode } from '@/features/signals/types'
import { TerrainSegmentedControl } from '@/components/ui/terrain'

type SignalFeedTabsProps = {
  viewMode: SignalViewMode
  onChange: (mode: SignalViewMode) => void
}

export function SignalFeedTabs({ viewMode, onChange }: SignalFeedTabsProps) {
  return (
    <TerrainSegmentedControl
      ariaLabel="Mode de vue"
      value={viewMode}
      onChange={onChange}
      options={[
        { value: 'personal', label: 'Ma zone' },
        { value: 'general', label: 'Vue globale' },
      ]}
    />
  )
}
