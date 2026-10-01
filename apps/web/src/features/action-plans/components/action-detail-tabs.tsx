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
    <div role="tablist" aria-label="Sections du plan d'action" className="flex w-full gap-5">
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
              'min-h-11 border-b-2 px-0.5 text-[13px] font-medium',
              isActive
                ? 'border-[#1a1a1a] text-[#1a1a1a]'
                : 'border-transparent text-[#7D7B75]',
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
