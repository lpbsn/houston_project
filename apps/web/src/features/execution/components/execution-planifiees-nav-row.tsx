import { ChevronRight } from 'lucide-react'

type ExecutionPlanifieesNavRowProps = {
  count: number
  prochaineLabel?: string | null
  onNavigate: () => void
}

export function ExecutionPlanifieesNavRow({
  count,
  prochaineLabel,
  onNavigate,
}: ExecutionPlanifieesNavRowProps) {
  return (
    <button
      type="button"
      className="flex min-h-11 w-full flex-col gap-0.5 rounded-[14px] border border-[#E8E6DF] bg-white px-3.5 py-2.5 text-left transition active:opacity-90"
      onClick={onNavigate}
      aria-label={`Planifiés, ${count}`}
    >
      <span className="flex w-full items-center gap-3">
        <span className="min-w-0 flex-1 text-sm font-semibold text-[#1a1a1a]">
          Planifiés
        </span>
        <span className="shrink-0 text-xs font-medium tabular-nums text-[#a3a19a]">
          {count}
        </span>
        <ChevronRight className="h-3.5 w-3.5 shrink-0 text-[#a3a19a]" aria-hidden />
      </span>
      {prochaineLabel ? (
        <span className="text-xs text-[#7D7B75]">{prochaineLabel}</span>
      ) : null}
    </button>
  )
}
