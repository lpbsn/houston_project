import { cn } from '@/lib/utils'

export type ActionDetailTab = 'details' | 'comments'

type ActionDetailTabsProps = {
  activeTab: ActionDetailTab
  onChange: (tab: ActionDetailTab) => void
}

const tabOptions: Array<{ value: ActionDetailTab; label: string }> = [
  { value: 'details', label: 'Détails' },
  { value: 'comments', label: 'Commentaires' },
]

export function ActionDetailTabs({ activeTab, onChange }: ActionDetailTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="Sections du plan d'action"
      className="grid w-full grid-cols-2 gap-1 rounded-xl bg-[#F5F4F0] p-1"
    >
      {tabOptions.map(({ value, label }) => {
        const isActive = activeTab === value

        return (
          <button
            key={value}
            type="button"
            role="tab"
            id={`execution-detail-tab-${value}`}
            aria-selected={isActive}
            aria-controls={`execution-detail-panel-${value}`}
            className={cn(
              'min-h-11 rounded-lg px-3 text-[14px] font-semibold transition',
              isActive ? 'bg-white text-[#1a1a1a] shadow-sm' : 'bg-transparent text-[#888]',
            )}
            onClick={() => onChange(value)}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
