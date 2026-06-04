type ActionDetailInstructionCardProps = {
  instruction: string
}

export function ActionDetailInstructionCard({ instruction }: ActionDetailInstructionCardProps) {
  const trimmed = instruction.trim()
  if (!trimmed) {
    return null
  }

  return (
    <div className="rounded-[14px] border border-[#E69138] bg-[#FFF9ED] p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.06em] text-[#B45309]">
        Consigne
      </p>
      <p className="mt-2 text-[13px] leading-relaxed text-[#444]">{trimmed}</p>
    </div>
  )
}
