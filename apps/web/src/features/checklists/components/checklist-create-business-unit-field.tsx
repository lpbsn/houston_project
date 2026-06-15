import { Check, ChevronRight } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { toRoleEnum } from '@/features/checklists/lib/checklist-role'
import { cn } from '@/lib/utils'

type ChecklistCreateBusinessUnitFieldProps = {
  establishmentId: string
  selectedBusinessUnitId: string
  selectedBusinessUnitLabel: string | null
  error?: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onBusinessUnitChange: (businessUnitId: string) => void
}

export function ChecklistCreateBusinessUnitField({
  establishmentId,
  selectedBusinessUnitId,
  selectedBusinessUnitLabel,
  error,
  open,
  onOpenChange,
  onBusinessUnitChange,
}: ChecklistCreateBusinessUnitFieldProps) {
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

  function handleSelect(businessUnitId: string) {
    onBusinessUnitChange(businessUnitId)
    onOpenChange(false)
  }

  return (
    <>
      <div className="space-y-1.5">
        <button
          type="button"
          aria-label="Pôle d'activité"
          className={cn(
            'flex min-h-11 w-full items-center justify-between rounded-xl border bg-white px-3 py-2.5 text-left',
            error ? 'border-destructive' : 'border-[#E8E6DF]',
          )}
          onClick={() => onOpenChange(true)}
        >
          <div className="min-w-0">
            <p className="text-sm font-medium text-[#1a1a1a]">Pôle d&apos;activité</p>
            <p className="truncate text-xs text-[#7D7B75]">
              {selectedBusinessUnitLabel ?? 'Sélectionnez un pôle'}
            </p>
          </div>
          <ChevronRight className="h-4 w-4 shrink-0 text-[#7D7B75]" aria-hidden />
        </button>
        {error ? <p className="text-xs text-destructive">{error}</p> : null}
      </div>

      <TerrainBottomSheet
        title="Pôle d'activité"
        open={open}
        onClose={() => onOpenChange(false)}
      >
        <div className="space-y-1 pb-2">
          {businessUnitQuery.isLoading ? (
            <p className="py-2 text-sm text-[#888]">Chargement des pôles…</p>
          ) : null}
          {businessUnitQuery.isError ? (
            <p className="text-sm text-destructive">Impossible de charger les pôles.</p>
          ) : null}
          {businessUnitQuery.isSuccess && businessUnits.length === 0 ? (
            <p className="py-2 text-sm text-[#888]">Aucun pôle disponible dans votre périmètre.</p>
          ) : null}
          {businessUnits.map((unit) => {
            const isSelected = selectedBusinessUnitId === unit.id
            return (
              <button
                key={unit.id}
                type="button"
                onClick={() => handleSelect(unit.id)}
                className={cn(
                  'flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-[14px] transition-colors',
                  isSelected
                    ? 'bg-[#EEF2FF] font-semibold text-[#1B4FD8]'
                    : 'text-[#444] hover:bg-[#F5F4F0]',
                )}
              >
                <span>{unit.label}</span>
                {isSelected ? <Check className="h-4 w-4" aria-hidden /> : null}
              </button>
            )
          })}
        </div>
      </TerrainBottomSheet>
    </>
  )
}
