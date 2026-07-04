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

function tabButtonClassName(active: boolean) {
  return cn(
    'min-h-11 rounded-xl border px-3 text-[14px] font-semibold transition',
    active
      ? 'border-[#1B4FD8] bg-[#1B4FD8] text-white'
      : 'border-[#E8E6DF] bg-white text-[#555]',
  )
}

export function ActionDetailTabs({ activeTab, onChange }: ActionDetailTabsProps) {
  return (
    <div
      role="group"
      aria-label="Sections de l'action"
      className="grid w-full grid-cols-2 gap-2"
    >
      {tabOptions.map(({ value, label }) => (
        <button
          key={value}
          type="button"
          aria-pressed={activeTab === value}
          className={tabButtonClassName(activeTab === value)}
          onClick={() => onChange(value)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
