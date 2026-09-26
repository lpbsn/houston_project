import type { ExecutionViewMode } from '@/features/execution/lib/types'
import { TerrainSegmentedControl } from '@/components/ui/terrain'

type ExecutionFeedTabsProps = {
  viewMode: ExecutionViewMode
  onChange: (mode: ExecutionViewMode) => void
  size?: 'default' | 'compact'
}

export function ExecutionFeedTabs({
  viewMode,
  onChange,
  size = 'default',
}: ExecutionFeedTabsProps) {
  return (
    <TerrainSegmentedControl
      ariaLabel="Mode de vue"
      className="w-fit"
      size={size}
      value={viewMode}
      onChange={onChange}
      options={[
        { value: 'personal', label: 'Ma vue' },
        { value: 'general', label: 'Vue globale' },
      ]}
    />
  )
}
