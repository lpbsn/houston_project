import { cn } from '@/lib/utils'

import type { EstablishmentAdminTab } from '../types'

type EstablishmentAdminTabsProps = {
  activeTab: EstablishmentAdminTab
  onChange: (tab: EstablishmentAdminTab) => void
}

const tabOptions: Array<{ value: EstablishmentAdminTab; label: string }> = [
  { value: 'overview', label: 'Vue d’ensemble' },
  { value: 'members', label: 'Membres' },
]

export function EstablishmentAdminTabs({ activeTab, onChange }: EstablishmentAdminTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="Sections de l’établissement"
      className="grid w-full grid-cols-2 gap-1 rounded-xl bg-[#F5F4F0] p-1"
    >
      {tabOptions.map(({ value, label }) => {
        const isActive = activeTab === value
        return (
          <button
            key={value}
            type="button"
            role="tab"
            id={`establishment-admin-tab-${value}`}
            aria-selected={isActive}
            aria-controls={`establishment-admin-panel-${value}`}
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
