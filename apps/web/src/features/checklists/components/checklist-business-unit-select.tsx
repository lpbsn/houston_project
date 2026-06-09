import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainSectionLabel } from '@/components/layout/terrain-card'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { toRoleEnum } from '@/features/checklists/lib/checklist-role'
import { cn } from '@/lib/utils'

type ChecklistBusinessUnitSelectProps = {
  establishmentId: string
  selectedBusinessUnitId: string
  onBusinessUnitChange: (businessUnitId: string) => void
  readOnlyLabel?: string | null
}

export function ChecklistBusinessUnitSelect({
  establishmentId,
  selectedBusinessUnitId,
  onBusinessUnitChange,
  readOnlyLabel,
}: ChecklistBusinessUnitSelectProps) {
  const { activeMembership } = useAuth()
  const role = toRoleEnum(activeMembership?.role)
  const businessUnitQuery = useBusinessUnitTreeQuery(establishmentId, { staleTime: 60_000 })

  const allBusinessUnits = businessUnitQuery.data?.business_units ?? []
  const managerScopes = activeMembership?.scopes ?? []
  const hasScopedRole = role === 'manager' || role === 'staff'
  const businessUnits =
    hasScopedRole && managerScopes.length > 0
      ? allBusinessUnits.filter((unit) =>
          managerScopes.some(
            (scope) => scope.scope_type === 'business_unit' && scope.scope_id === unit.id,
          ),
        )
      : allBusinessUnits

  if (readOnlyLabel) {
    return (
      <section className="space-y-1.5">
        <TerrainSectionLabel>Pôle</TerrainSectionLabel>
        <TerrainCard>
          <p className="text-sm font-medium text-[#1a1a1a]">{readOnlyLabel}</p>
          <p className="mt-1 text-xs text-[#7D7B75]">
            Le pôle ne peut pas être modifié après la création.
          </p>
        </TerrainCard>
      </section>
    )
  }

  if (businessUnitQuery.isLoading) {
    return (
      <div className="flex items-center gap-2 py-2 text-sm text-[#888]">
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
        Chargement des pôles…
      </div>
    )
  }

  if (businessUnitQuery.isError) {
    return <p className="text-sm text-destructive">Impossible de charger les pôles.</p>
  }

  return (
    <section className="space-y-1.5">
      <TerrainSectionLabel>Pôle</TerrainSectionLabel>
      <TerrainCard className="flex flex-col gap-1 p-1">
        {businessUnits.length === 0 ? (
          <p className="px-2 py-2 text-sm text-[#888]">Aucun pôle disponible dans votre périmètre.</p>
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
