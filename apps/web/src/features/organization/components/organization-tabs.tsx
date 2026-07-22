import { cn } from '@/lib/utils'

import type { OrganizationTab } from '../types'

type OrganizationTabsProps = {
  activeTab: OrganizationTab
  onChange: (tab: OrganizationTab) => void
}

const tabOptions: Array<{ value: OrganizationTab; label: string }> = [
  { value: 'establishments', label: 'Établissements' },
  { value: 'members', label: 'Membres' },
  { value: 'owners', label: 'Propriétaires' },
]

export function OrganizationTabs({ activeTab, onChange }: OrganizationTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="Sections de l’organisation"
      className="grid w-full grid-cols-3 gap-1 rounded-xl bg-[#F5F4F0] p-1"
    >
      {tabOptions.map(({ value, label }) => {
        const isActive = activeTab === value
        return (
          <button
            key={value}
            type="button"
            role="tab"
            id={`organization-tab-${value}`}
            aria-selected={isActive}
            aria-controls={`organization-panel-${value}`}
            className={cn(
              'min-h-11 rounded-lg px-2 text-[13px] font-semibold transition sm:text-[14px]',
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
