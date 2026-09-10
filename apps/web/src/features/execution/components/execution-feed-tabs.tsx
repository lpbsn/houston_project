import type { ExecutionViewMode } from '@/features/execution/lib/types'
import { TerrainSegmentedControl } from '@/components/ui/terrain'

type ExecutionFeedTabsProps = {
  viewMode: ExecutionViewMode
  onChange: (mode: ExecutionViewMode) => void
}

export function ExecutionFeedTabs({ viewMode, onChange }: ExecutionFeedTabsProps) {
  return (
    <TerrainSegmentedControl
      ariaLabel="Mode de vue"
      className="w-fit"
      value={viewMode}
      onChange={onChange}
      options={[
        { value: 'personal', label: 'Ma vue' },
        { value: 'general', label: 'Vue globale' },
      ]}
    />
  )
}
