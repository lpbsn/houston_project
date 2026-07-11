import type { ExecutionViewMode } from '@/features/execution/lib/types'
import { TerrainFilterPill } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

type ExecutionFeedTabsProps = {
  viewMode: ExecutionViewMode
  onChange: (mode: ExecutionViewMode) => void
}

function executionTabPillClassName(active: boolean): string {
  return cn('uppercase', active && 'border-[#114660] bg-[#114660] text-white')
}

export function ExecutionFeedTabs({ viewMode, onChange }: ExecutionFeedTabsProps) {
  return (
    <div className="flex gap-1.5 overflow-x-auto">
      <TerrainFilterPill
        active={viewMode === 'personal'}
        onClick={() => onChange('personal')}
        className={executionTabPillClassName(viewMode === 'personal')}
      >
        Ma vue
      </TerrainFilterPill>
      <TerrainFilterPill
        active={viewMode === 'general'}
        onClick={() => onChange('general')}
        className={executionTabPillClassName(viewMode === 'general')}
      >
        Vue globale
      </TerrainFilterPill>
    </div>
  )
}
