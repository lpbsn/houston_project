import { cn } from '@/lib/utils'

export type SignalDetailTab = 'details' | 'comments'

type SignalDetailTabsProps = {
  activeTab: SignalDetailTab
  onChange: (tab: SignalDetailTab) => void
}

const tabOptions: Array<{ value: SignalDetailTab; label: string }> = [
  { value: 'details', label: 'Détails' },
  { value: 'comments', label: 'Commentaires' },
]

export function SignalDetailTabs({ activeTab, onChange }: SignalDetailTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="Sections de l'observation"
      className="grid w-full grid-cols-2 gap-0.5 rounded-lg bg-[#EFEDE8]/80 p-0.5"
    >
      {tabOptions.map(({ value, label }) => {
        const isActive = activeTab === value

        return (
          <button
            key={value}
            type="button"
            role="tab"
            id={`signal-detail-tab-${value}`}
            aria-selected={isActive}
            aria-controls={`signal-detail-panel-${value}`}
            className={cn(
              'min-h-12 rounded-md px-3 text-[13px] font-medium transition-colors',
              isActive
                ? 'z-10 bg-white/90 text-[#1a1a1a]'
                : 'z-0 bg-transparent text-[#8A8780]',
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
