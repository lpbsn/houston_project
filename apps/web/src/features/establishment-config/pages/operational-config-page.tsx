import { ArrowLeft, LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { OperationalConfigBusinessUnitCard } from '@/features/establishment-config/components/operational-config-business-unit-card'
import { RuntimeConfigApiError } from '@/features/establishment-config/api'
import {
  useCreateRuntimeBusinessUnit,
  useOperationalConfigTree,
} from '@/features/establishment-config/hooks'
import { BusinessUnitAutocomplete } from '@/features/onboarding/components/business-unit-autocomplete'
import type { CatalogBusinessUnitSuggestion } from '@/features/onboarding/types'

type OperationalConfigPageProps = {
  onNavigate?: (path: string) => void
}

function OperationalConfigContent({
  establishmentId,
  establishmentName,
  onNavigate,
}: {
  establishmentId: string
  establishmentName: string
  onNavigate?: (path: string) => void
}) {
  const treeQuery = useOperationalConfigTree(establishmentId)
  const createBusinessUnitMutation = useCreateRuntimeBusinessUnit(establishmentId)
  const [pageError, setPageError] = useState<string | null>(null)
  const [pageFeedback, setPageFeedback] = useState<string | null>(null)

  const businessUnits = treeQuery.data?.business_units ?? []

  async function handleAddBusinessUnit(input: {
    label: string
    catalog_key?: string | null
    unit_type?: string
  }) {
    setPageError(null)
    setPageFeedback(null)

    try {
      await createBusinessUnitMutation.mutateAsync({
        label: input.label,
        catalog_key: input.catalog_key ?? null,
        unit_type: input.unit_type,
      })
      setPageFeedback('Pôle ajouté.')
    } catch (error) {
      setPageError(
        error instanceof RuntimeConfigApiError
          ? error.message
          : 'Le pôle n’a pas pu être ajouté.',
      )
    }
  }

  function handleSelectSuggestion(suggestion: CatalogBusinessUnitSuggestion) {
    void handleAddBusinessUnit({
      label: suggestion.label,
      catalog_key: suggestion.key,
      unit_type: suggestion.default_unit_type,
    })
  }

  function handleAddFreeText(label: string) {
    void handleAddBusinessUnit({ label })
  }

  if (treeQuery.isPending) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <LoaderCircle className="size-4 animate-spin" />
        Chargement de la configuration opérationnelle…
      </div>
    )
  }

  if (treeQuery.error) {
    return (
      <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9]">
        <CardHeader>
          <CardTitle>Erreur de chargement</CardTitle>
          <CardDescription>
            {treeQuery.error instanceof RuntimeConfigApiError
              ? treeQuery.error.message
              : 'La configuration opérationnelle n’a pas pu être chargée.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            type="button"
            variant="outline"
            className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
            onClick={() => {
              void treeQuery.refetch()
            }}
          >
            Réessayer
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4 sm:space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">Configuration opérationnelle</p>
          <h2 className="text-2xl font-black tracking-[-0.04em]">
            {treeQuery.data?.establishment_name ?? establishmentName}
          </h2>
        </div>
        <Button
          type="button"
          variant="outline"
          className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
          onClick={() => onNavigate?.('/app')}
        >
          <ArrowLeft className="size-4" />
          Retour à la gestion
        </Button>
      </div>

      <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9]">
        <CardHeader className="gap-2">
          <CardTitle className="text-lg font-semibold">Ajouter un pôle</CardTitle>
          <CardDescription className="text-sm">
            Recherchez dans le catalogue ou saisissez un libellé libre.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <BusinessUnitAutocomplete
            disabled={createBusinessUnitMutation.isPending}
            onAddFreeText={handleAddFreeText}
            onSelectSuggestion={handleSelectSuggestion}
          />
        </CardContent>
      </Card>

      {pageFeedback ? <p className="text-sm text-emerald-700">{pageFeedback}</p> : null}
      {pageError ? <p className="text-sm text-destructive">{pageError}</p> : null}

      {businessUnits.length === 0 ? (
        <Card className="rounded-[1.75rem] border-dashed border-[#ece5da] bg-[#fffdf9]">
          <CardHeader>
            <CardTitle>Aucun pôle actif</CardTitle>
            <CardDescription>
              Ajoutez votre premier pôle pour commencer la configuration runtime.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        businessUnits.map((businessUnit) => (
          <OperationalConfigBusinessUnitCard
            key={`${businessUnit.id}:${businessUnit.description}:${businessUnit.activity_subjects.length}`}
            businessUnit={businessUnit}
            establishmentId={establishmentId}
            canRemoveBusinessUnit={businessUnits.length > 1}
          />
        ))
      )}
    </div>
  )
}

export function OperationalConfigPage({ onNavigate }: OperationalConfigPageProps) {
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id

  if (!establishmentId) {
    return (
      <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9]">
        <CardHeader>
          <CardTitle>Configuration indisponible</CardTitle>
          <CardDescription>
            Sélectionnez un établissement actif pour modifier la configuration opérationnelle.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <OperationalConfigContent
      establishmentId={establishmentId}
      establishmentName={activeMembership.establishment_name}
      onNavigate={onNavigate}
    />
  )
}
