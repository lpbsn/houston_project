import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { OperationalConfigBusinessUnitCard } from '@/features/establishment-config/components/operational-config-business-unit-card'
import {
  useCreateRuntimeBusinessUnit,
  useOperationalConfigTree,
} from '@/features/establishment-config/hooks'
import { canManageOperationalConfigForEstablishment } from '@/features/establishment-config/lib/can-manage-operational-config'
import { resolveRuntimeConfigErrorMessage } from '@/features/establishment-config/lib/runtime-config-errors'
import { BusinessUnitAutocomplete } from '@/features/onboarding/components/business-unit-autocomplete'
import type { CatalogBusinessUnitSuggestion } from '@/features/onboarding/types'

type OperationalConfigPageProps = {
  establishmentId: string
}

function OperationalConfigContent({ establishmentId }: { establishmentId: string }) {
  const treeQuery = useOperationalConfigTree(establishmentId)
  const createBusinessUnitMutation = useCreateRuntimeBusinessUnit(establishmentId)
  const [pageError, setPageError] = useState<string | null>(null)
  const [pageFeedback, setPageFeedback] = useState<string | null>(null)

  const businessUnits = treeQuery.data?.business_units ?? []

  async function handleAddBusinessUnit(input: {
    specific_name: string
    catalog_key: string
  }) {
    setPageError(null)
    setPageFeedback(null)

    try {
      await createBusinessUnitMutation.mutateAsync({
        specific_name: input.specific_name,
        catalog_key: input.catalog_key,
      })
      setPageFeedback('Pôle ajouté.')
    } catch (error) {
      setPageError(resolveRuntimeConfigErrorMessage(error, 'Le pôle n’a pas pu être ajouté.'))
    }
  }

  function handleSelectSuggestion(suggestion: CatalogBusinessUnitSuggestion) {
    void handleAddBusinessUnit({
      specific_name: suggestion.label,
      catalog_key: suggestion.key,
    })
  }

  function handleAddFreeText() {
    setPageError('Sélectionnez un pôle catalogue pour créer une instance.')
  }

  if (treeQuery.isPending) {
    return (
      <div className="flex items-center gap-2 px-4 py-5 text-sm text-muted-foreground">
        <LoaderCircle className="size-4 animate-spin" />
        Chargement de la configuration opérationnelle…
      </div>
    )
  }

  if (treeQuery.error) {
    return (
      <Card className="mx-4 my-5 rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9]">
        <CardHeader>
          <CardTitle>Erreur de chargement</CardTitle>
          <CardDescription>
            {resolveRuntimeConfigErrorMessage(
              treeQuery.error,
              'La configuration opérationnelle n’a pas pu être chargée.',
            )}
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
    <div className="space-y-4 px-4 py-5 sm:space-y-5">
      <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9]">
        <CardHeader className="gap-2">
          <CardTitle className="text-lg font-semibold">Ajouter un pôle</CardTitle>
          <CardDescription className="text-sm">
            Recherchez un pôle catalogue, puis créez une instance nommée.
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
            key={`${businessUnit.id}:${businessUnit.instance_description}:${businessUnit.activity_subjects.length}:${businessUnit.active}`}
            businessUnit={businessUnit}
            establishmentId={establishmentId}
            canRemoveBusinessUnit={
              businessUnits.filter((item) => item.active).length > 1 && businessUnit.active
            }
          />
        ))
      )}
    </div>
  )
}

function OperationalConfigAccessDenied() {
  return (
    <Card className="mx-4 my-5 rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9]">
      <CardHeader>
        <CardTitle>Accès refusé</CardTitle>
        <CardDescription>
          Seuls le propriétaire et le directeur peuvent modifier la configuration opérationnelle.
        </CardDescription>
      </CardHeader>
    </Card>
  )
}

export function OperationalConfigPage({ establishmentId }: OperationalConfigPageProps) {
  const { activeMembership, bootstrap } = useAuth()
  const sessionEstablishmentId = activeMembership?.establishment_id
  const canManage = canManageOperationalConfigForEstablishment({
    memberships: bootstrap?.memberships,
    establishmentId,
  })

  if (!canManage) {
    return <OperationalConfigAccessDenied />
  }

  if (sessionEstablishmentId !== establishmentId) {
    return (
      <div className="flex items-center gap-2 px-4 py-5 text-sm text-muted-foreground">
        <LoaderCircle className="size-4 animate-spin" />
        Chargement de la configuration opérationnelle…
      </div>
    )
  }

  return <OperationalConfigContent establishmentId={establishmentId} />
}
