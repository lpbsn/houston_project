import { LoaderCircle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  isBusinessUnitSelected,
  toggleBusinessUnitScope,
  type BusinessUnitScopeSelection,
  type BusinessUnitTree,
} from '@/features/auth/lib/business-unit-scope'

type BusinessUnitScopeSelectorProps = {
  disabled?: boolean
  errorMessage?: string | null
  isLoading?: boolean
  onChange: (scopes: BusinessUnitScopeSelection[]) => void
  readOnly?: boolean
  selectedScopes: BusinessUnitScopeSelection[]
  tree: BusinessUnitTree | null
}

export function BusinessUnitScopeSelector({
  disabled = false,
  errorMessage = null,
  isLoading = false,
  onChange,
  readOnly = false,
  selectedScopes,
  tree,
}: BusinessUnitScopeSelectorProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <LoaderCircle className="size-4 animate-spin" />
        Chargement des pôles d&apos;activité…
      </div>
    )
  }

  if (!tree?.business_units.length) {
    return (
      <p className="text-sm text-muted-foreground">
        Aucun pôle d&apos;activité configuré pour cet établissement.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Sélectionnez un ou plusieurs pôles d&apos;activité (BusinessUnit).
      </p>
      <div className="space-y-2">
        {tree.business_units.map((bu) => {
          const selected = isBusinessUnitSelected(selectedScopes, bu.id)
          return (
            <label
              key={bu.id}
              className={cn(
                'flex cursor-pointer items-start gap-3 rounded-lg border p-3',
                selected && 'border-primary bg-primary/5',
                (disabled || readOnly) && 'cursor-default opacity-70',
              )}
            >
              <input
                type="checkbox"
                checked={selected}
                disabled={disabled || readOnly}
                onChange={() => onChange(toggleBusinessUnitScope(selectedScopes, bu.id))}
                className="mt-1"
              />
              <span className="flex-1 space-y-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{bu.label}</span>
                  <Badge variant="outline">{bu.unit_type}</Badge>
                </span>
                {bu.activity_subjects.length > 0 ? (
                  <span className="block text-xs text-muted-foreground">
                    {bu.activity_subjects.length} sujet(s) configuré(s)
                  </span>
                ) : null}
              </span>
            </label>
          )
        })}
      </div>
      {errorMessage ? <p className="text-sm text-destructive">{errorMessage}</p> : null}
    </div>
  )
}
