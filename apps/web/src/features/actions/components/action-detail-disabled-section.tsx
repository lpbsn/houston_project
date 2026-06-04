import { Camera, Paperclip, Pencil } from 'lucide-react'

import { HoustonBadge, TerrainCard, TerrainFieldLabel } from '@/components/ui/terrain'

function DisabledSoonBadge() {
  return (
    <HoustonBadge variant="gray" className="text-[8px]">
      Bientôt
    </HoustonBadge>
  )
}

type ActionDetailCommentsDisabledSectionProps = {
  description?: string
}

export function ActionDetailCommentsDisabledSection({
  description = 'Bientôt disponible',
}: ActionDetailCommentsDisabledSectionProps = {}) {
  return (
    <TerrainCard
      className="pointer-events-none opacity-60"
      aria-disabled="true"
      aria-label="Commentaires — bientôt disponible"
    >
      <div className="flex items-center justify-between gap-2">
        <TerrainFieldLabel>Commentaires</TerrainFieldLabel>
        <DisabledSoonBadge />
      </div>
      <div className="mt-3 rounded-[10px] border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5">
        <p className="text-[12px] text-[#aaa]">{description}</p>
      </div>
    </TerrainCard>
  )
}

export function ActionDetailProofDisabledSection() {
  return (
    <div
      className="pointer-events-none rounded-[14px] border border-[#E8E6DF] bg-[#F0EFE9] p-4 opacity-60"
      aria-disabled="true"
      aria-label="Ajouter une preuve — bientôt disponible"
    >
      <div className="flex items-center gap-3">
        <Paperclip className="h-4 w-4 shrink-0 text-[#888]" aria-hidden />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-[13px] font-semibold text-[#1a1a1a]">Ajouter une preuve</p>
            <DisabledSoonBadge />
          </div>
          <p className="mt-0.5 text-[11px] text-[#888]">
            Photo ou description de ce qui a été fait
          </p>
        </div>
        <div className="flex shrink-0 gap-1.5" aria-hidden>
          <div className="flex h-8 w-8 items-center justify-center rounded-[8px] border border-[#E8E6DF] bg-white">
            <Camera className="h-4 w-4 text-[#888]" />
          </div>
          <div className="flex h-8 w-8 items-center justify-center rounded-[8px] border border-[#E8E6DF] bg-white">
            <Pencil className="h-4 w-4 text-[#888]" />
          </div>
        </div>
      </div>
    </div>
  )
}
