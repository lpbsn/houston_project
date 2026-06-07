import { Trash2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { BusinessUnitAutocomplete } from '@/features/onboarding/components/business-unit-autocomplete'
import type { CatalogBusinessUnitSuggestion } from '@/features/onboarding/types'
import {
  createDraftBusinessUnit,
  type DraftBusinessUnit,
} from '@/features/onboarding/lib/manual-v2-proposal'

type ManualOnboardingV2BuPickerStepProps = {
  businessUnits: DraftBusinessUnit[]
  disabled?: boolean
  onChange: (businessUnits: DraftBusinessUnit[]) => void
}

function hasDuplicateLabel(businessUnits: DraftBusinessUnit[], label: string) {
  const normalized = label.trim().toLowerCase()
  return businessUnits.some((item) => item.label.trim().toLowerCase() === normalized)
}

export function ManualOnboardingV2BuPickerStep({
  businessUnits,
  disabled = false,
  onChange,
}: ManualOnboardingV2BuPickerStepProps) {
  function addBusinessUnit(draft: DraftBusinessUnit) {
    if (hasDuplicateLabel(businessUnits, draft.label)) {
      return
    }

    onChange([...businessUnits, draft])
  }

  function handleSelectSuggestion(suggestion: CatalogBusinessUnitSuggestion) {
    const suggestedUnitType =
      suggestion.default_unit_type === 'transversal' ? 'transversal' : 'dedicated'

    addBusinessUnit(
      createDraftBusinessUnit({
        label: suggestion.label,
        suggested_unit_type: suggestedUnitType,
        catalog_key: suggestion.key,
      }),
    )
  }

  function handleAddFreeText(label: string) {
    addBusinessUnit(createDraftBusinessUnit({ label }))
  }

  function handleRemove(clientKey: string) {
    onChange(businessUnits.filter((item) => item.client_key !== clientKey))
  }

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-semibold">Étape 1 — Pôles d&apos;activité</h3>
        <p className="text-sm leading-6 text-muted-foreground">
          Ajoutez au moins un pôle d&apos;activité. Utilisez le catalogue pour des suggestions ou
          saisissez un libellé libre. Vous choisirez le type (dédié ou transversal) à l&apos;étape
          suivante.
        </p>
      </div>

      <BusinessUnitAutocomplete
        disabled={disabled}
        onAddFreeText={handleAddFreeText}
        onSelectSuggestion={handleSelectSuggestion}
      />

      {businessUnits.length > 0 ? (
        <ul className="space-y-2">
          {businessUnits.map((businessUnit) => (
            <li
              key={businessUnit.client_key}
              className="flex items-center justify-between rounded-[1rem] border border-[#ece5da] bg-white px-4 py-3"
            >
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{businessUnit.label}</span>
                  {businessUnit.catalog_key ? (
                    <Badge variant="secondary">catalogue</Badge>
                  ) : (
                    <Badge variant="secondary">libre</Badge>
                  )}
                </div>
                {businessUnit.catalog_key ? (
                  <p className="text-xs text-muted-foreground">{businessUnit.catalog_key}</p>
                ) : null}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={disabled}
                onClick={() => handleRemove(businessUnit.client_key)}
                aria-label={`Retirer ${businessUnit.label}`}
              >
                <Trash2 className="size-4" />
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">Aucun pôle ajouté pour le moment.</p>
      )}
    </div>
  )
}
