import type { SignalViewMode } from '@/features/signals/types'
import { TerrainFilterPill } from '@/components/ui/terrain'

type SignalFeedTabsProps = {
  viewMode: SignalViewMode
  onChange: (mode: SignalViewMode) => void
}

export function SignalFeedTabs({ viewMode, onChange }: SignalFeedTabsProps) {
  return (
    <div className="flex gap-1.5 overflow-x-auto">
      <TerrainFilterPill
        active={viewMode === 'personal'}
        onClick={() => onChange('personal')}
      >
        Ma zone
      </TerrainFilterPill>
      <TerrainFilterPill active={viewMode === 'general'} onClick={() => onChange('general')}>
        Vue globale
      </TerrainFilterPill>
    </div>
  )
}
