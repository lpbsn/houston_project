import type { SignalViewMode } from '@/features/signals/types'

type SignalFeedTabsProps = {
  viewMode: SignalViewMode
  onChange: (mode: SignalViewMode) => void
}

export function SignalFeedTabs({ viewMode, onChange }: SignalFeedTabsProps) {
  return (
    <div className="flex gap-2 rounded-2xl border border-[#e7dfd1] bg-[#fffaf2] p-1">
      <button
        type="button"
        className={`flex-1 rounded-xl px-3 py-2 text-sm font-semibold transition ${
          viewMode === 'personal'
            ? 'bg-[#1b4fd8] text-white'
            : 'text-[#6b5f52] hover:bg-[#f5f4f0]'
        }`}
        onClick={() => onChange('personal')}
      >
        Ma zone
      </button>
      <button
        type="button"
        className={`flex-1 rounded-xl px-3 py-2 text-sm font-semibold transition ${
          viewMode === 'general'
            ? 'bg-[#1b4fd8] text-white'
            : 'text-[#6b5f52] hover:bg-[#f5f4f0]'
        }`}
        onClick={() => onChange('general')}
      >
        Vue globale
      </button>
    </div>
  )
}
