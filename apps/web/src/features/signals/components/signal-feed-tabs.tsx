import type { SignalViewMode } from '@/features/signals/types'
import { TerrainFilterPill } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

type SignalFeedTabsProps = {
  viewMode: SignalViewMode
  onChange: (mode: SignalViewMode) => void
}

function signalTabPillClassName(active: boolean): string {
  return cn('uppercase', active && 'border-[#114660] bg-[#114660] text-white')
}

export function SignalFeedTabs({ viewMode, onChange }: SignalFeedTabsProps) {
  return (
    <div className="flex gap-1.5 overflow-x-auto">
      <TerrainFilterPill
        active={viewMode === 'personal'}
        onClick={() => onChange('personal')}
        className={signalTabPillClassName(viewMode === 'personal')}
      >
        Ma zone
      </TerrainFilterPill>
      <TerrainFilterPill
        active={viewMode === 'general'}
        onClick={() => onChange('general')}
        className={signalTabPillClassName(viewMode === 'general')}
      >
        Vue globale
      </TerrainFilterPill>
    </div>
  )
}
