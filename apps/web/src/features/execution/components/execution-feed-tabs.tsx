import type { ExecutionViewMode } from '@/features/actions/types'
import { TerrainFilterPill } from '@/components/ui/terrain'

type ExecutionFeedTabsProps = {
  viewMode: ExecutionViewMode
  onChange: (mode: ExecutionViewMode) => void
}

export function ExecutionFeedTabs({ viewMode, onChange }: ExecutionFeedTabsProps) {
  return (
    <div className="flex gap-1.5 overflow-x-auto">
      <TerrainFilterPill
        active={viewMode === 'personal'}
        onClick={() => onChange('personal')}
      >
        Ma vue
      </TerrainFilterPill>
      <TerrainFilterPill active={viewMode === 'general'} onClick={() => onChange('general')}>
        Vue globale
      </TerrainFilterPill>
    </div>
  )
}
