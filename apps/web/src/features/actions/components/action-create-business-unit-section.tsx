import { LoaderCircle } from 'lucide-react'

import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { cn } from '@/lib/utils'

type ActionCreateBusinessUnitSectionProps = {
  establishmentId: string
  selectedBusinessUnitId: string
  onBusinessUnitChange: (businessUnitId: string) => void
}

export function ActionCreateBusinessUnitSection({
  establishmentId,
  selectedBusinessUnitId,
  onBusinessUnitChange,
}: ActionCreateBusinessUnitSectionProps) {
  const businessUnitQuery = useBusinessUnitTreeQuery(establishmentId, { staleTime: 60_000 })

  if (businessUnitQuery.isLoading) {
    return (
      <div className="flex items-center gap-2 py-2 text-sm text-[#888]">
        <LoaderCircle className="h-4 w-4 animate-spin" />
        Chargement des pôles…
      </div>
    )
  }

  if (businessUnitQuery.isError || !businessUnitQuery.data) {
    return (
      <p className="text-sm text-destructive">
        Impossible de charger les pôles d&apos;activité.
      </p>
    )
  }

  const businessUnits = businessUnitQuery.data.business_units

  return (
    <section className="flex flex-col gap-1.5">
      <TerrainSectionLabel>Pôle d&apos;activité responsable</TerrainSectionLabel>
      <TerrainCard className="flex flex-col gap-1 p-1">
        {businessUnits.length === 0 ? (
          <p className="px-2 py-2 text-sm text-[#888]">Aucun pôle disponible.</p>
        ) : (
          businessUnits.map((unit) => {
            const isSelected = selectedBusinessUnitId === unit.id
            return (
              <button
                key={unit.id}
                type="button"
                onClick={() => onBusinessUnitChange(unit.id)}
                className={cn(
                  'rounded-xl px-3 py-2.5 text-left text-[14px] transition-colors',
                  isSelected
                    ? 'bg-[#EEF2FF] font-semibold text-[#1B4FD8]'
                    : 'text-[#444] hover:bg-[#F5F4F0]',
                )}
              >
                {unit.label}
              </button>
            )
          })
        )}
      </TerrainCard>
    </section>
  )
}
