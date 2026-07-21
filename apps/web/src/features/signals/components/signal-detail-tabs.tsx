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
      className="grid w-full grid-cols-2 gap-1 rounded-xl bg-[#F5F4F0] p-1"
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
