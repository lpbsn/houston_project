import { ClipboardList } from 'lucide-react'

type ActionDetailInstructionCardProps = {
  instruction: string
}

export function ActionDetailInstructionCard({ instruction }: ActionDetailInstructionCardProps) {
  const trimmed = instruction.trim()
  if (!trimmed) {
    return null
  }

  return (
    <div className="rounded-2xl border border-[#D9B38C] bg-[#FEF9EC] p-5">
      <div className="flex items-center gap-2">
        <ClipboardList className="h-4 w-4 shrink-0 text-[#B87333]" aria-hidden />
        <p className="text-[11px] font-bold uppercase tracking-[0.04em] text-[#B87333]">
          Consigne
        </p>
      </div>
      <p className="mt-3 text-[15px] font-medium leading-relaxed text-[#4A3728]">{trimmed}</p>
    </div>
  )
}
