import { ChevronRight } from 'lucide-react'

type ExecutionUpcomingNavRowProps = {
  count: number
  onNavigate: () => void
}

export function ExecutionUpcomingNavRow({ count, onNavigate }: ExecutionUpcomingNavRowProps) {
  return (
    <button
      type="button"
      className="flex min-h-11 w-full items-center gap-3 rounded-[14px] border border-[#E8E6DF] bg-white px-3.5 py-2.5 text-left transition active:opacity-90"
      onClick={onNavigate}
      aria-label={`À venir, ${count}`}
    >
      <span className="min-w-0 flex-1 text-sm font-semibold text-[#1a1a1a]">À venir</span>
      <span className="shrink-0 text-sm font-semibold tabular-nums text-[#7D7B75]">{count}</span>
      <ChevronRight className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
    </button>
  )
}
