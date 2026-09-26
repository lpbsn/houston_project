import type { SignalViewMode } from '@/features/signals/types'
import { TerrainSegmentedControl } from '@/components/ui/terrain'

type SignalFeedTabsProps = {
  viewMode: SignalViewMode
  onChange: (mode: SignalViewMode) => void
  size?: 'default' | 'compact'
}

export function SignalFeedTabs({
  viewMode,
  onChange,
  size = 'default',
}: SignalFeedTabsProps) {
  return (
    <TerrainSegmentedControl
      ariaLabel="Mode de vue"
      className="w-fit"
      size={size}
      value={viewMode}
      onChange={onChange}
      options={[
        { value: 'personal', label: 'Ma zone' },
        { value: 'general', label: 'Vue globale' },
      ]}
    />
  )
}
