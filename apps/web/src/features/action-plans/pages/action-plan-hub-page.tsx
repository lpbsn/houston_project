import { Plus } from 'lucide-react'
import { useMemo, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import {
  canViewActionPlanCatalogFromBootstrapHints,
  canCreateCatalogActionPlanFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { TerrainCard } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { terrain, terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanCatalogSectionView } from '../components/action-plan-catalog-section'
import { ActionPlanHubFilters } from '../components/action-plan-hub-filters'
import { ActionPlanUseSheet } from '../components/action-plan-use-sheet'
import {
  useActionPlanCatalogQuery,
  useScheduleActionPlanFromCatalogMutation,
  useUseActionPlanFromCatalogMutation,
} from '../hooks'
import { filterActionPlansByTitle } from '../lib/action-plan-catalog-filters'
import {
  canAccessActionPlanCatalog,
  isStaffActionPlanUsageRole,
} from '../lib/action-plan-management-access'
import { groupActionPlansByPilotBusinessUnit } from '../lib/action-plan-display'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import { canShowActionPlanSchedule } from '../lib/action-plan-permission-hints'
import type { CatalogPlanningSubmit } from '../lib/action-plan-catalog-planning-submit'
import type { ActionPlanCatalogListFilters } from '../types'

type ActionPlanHubPageProps = {
  onNavigate?: (pathname: string) => void
}

export function ActionPlanHubPage({ onNavigate }: ActionPlanHubPageProps) {
  const { navigate } = useAppRoute()
  const navigateTo = onNavigate ?? navigate
  const { activeMembership, bootstrap, isBootstrapping, isReady } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null
  const membershipId = activeMembership?.id ?? null
  const role = activeMembership?.role ?? null
  const permissionHints = getBootstrapPermissionHints(bootstrap)

  const canAccessLibrary = canAccessActionPlanCatalog({
    establishmentId,
    activeMembershipId: membershipId,
    role,
    canViewActionPlanCatalog: canViewActionPlanCatalogFromBootstrapHints(permissionHints),
  })
  const canCreate = canCreateCatalogActionPlanFromBootstrapHints(permissionHints)
  const staffUseMode = isStaffActionPlanUsageRole(role)

  const [searchQuery, setSearchQuery] = useState('')
  const [businessUnitId, setBusinessUnitId] = useState('')
  const [createdByMe, setCreatedByMe] = useState(false)
  const [usePlanId, setUsePlanId] = useState<string | null>(null)
  const [useError, setUseError] = useState<string | null>(null)

  const filters = useMemo<ActionPlanCatalogListFilters>(() => {
    const next: ActionPlanCatalogListFilters = {}
    if (createdByMe) {
      next.created_by_me = true
    }
    if (businessUnitId) {
      next.business_unit_id = businessUnitId
    }
    return next
  }, [businessUnitId, createdByMe])

  const catalogQuery = useActionPlanCatalogQuery(
    canAccessLibrary ? establishmentId : null,
    filters,
  )
  const useMutation = useUseActionPlanFromCatalogMutation(establishmentId ?? '')
  const scheduleMutation = useScheduleActionPlanFromCatalogMutation(establishmentId ?? '')

  const filteredItems = useMemo(() => {
    const items = catalogQuery.data ?? []
    return filterActionPlansByTitle(items, searchQuery)
  }, [catalogQuery.data, searchQuery])

  const sections = useMemo(
    () => groupActionPlansByPilotBusinessUnit(filteredItems),
    [filteredItems],
  )

  const usePlan = catalogQuery.data?.find((item) => item.id === usePlanId) ?? null

  if (!isReady || isBootstrapping) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!canAccessLibrary) {
    return (
      <div className="px-3 py-4">
        <TerrainCard>
          <p className={cn('text-sm', terrain.muted)}>
            Vous n&apos;avez pas accès à la bibliothèque de plans d&apos;action.
          </p>
        </TerrainCard>
      </div>
    )
  }

  if (catalogQuery.isError && catalogQuery.error && 'status' in catalogQuery.error) {
    const status = (catalogQuery.error as { status?: number }).status
    if (status === 403 || status === 404) {
      return (
        <div className="px-3 py-4">
          <TerrainCard>
            <p className={cn('text-sm', terrain.muted)}>
              Vous n&apos;avez pas accès à la bibliothèque de plans d&apos;action.
            </p>
          </TerrainCard>
        </div>
      )
    }
  }

  async function handlePlanningSubmit(result: CatalogPlanningSubmit) {
    if (!usePlanId) {
      return
    }

    setUseError(null)
    try {
      if (result.kind === 'schedule') {
        await scheduleMutation.mutateAsync({ actionPlanId: usePlanId, body: result.scheduleBody })
        setUsePlanId(null)
        return
      }

      if (result.kind === 'mixed') {
        await scheduleMutation.mutateAsync({ actionPlanId: usePlanId, body: result.scheduleBody })
        const execution = await useMutation.mutateAsync({
          actionPlanId: usePlanId,
          body: result.useBody,
        })
        setUsePlanId(null)
        navigateTo(`/action-plans/executions/${execution.id}`)
        return
      }

      const execution = await useMutation.mutateAsync({
        actionPlanId: usePlanId,
        body: result.useBody,
      })
      setUsePlanId(null)
      navigateTo(`/action-plans/executions/${execution.id}`)
    } catch (error) {
      const message =
        result.kind === 'schedule'
          ? 'Le plan n’a pas pu être planifié.'
          : result.kind === 'mixed'
            ? 'Le plan n’a pas pu être lancé.'
            : 'Le plan n’a pas pu être utilisé.'
      setUseError(resolveActionPlanErrorMessage(error, message))
    }
  }

  return (
    <div className="space-y-4 px-4 pb-24 pt-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-bold text-[#1a1a1a]">Bibliothèque</h1>
          <p className="mt-1 text-sm text-[#7D7B75]">
            Modèles de plans d&apos;action prêts à lancer sur le terrain.
          </p>
        </div>
        {canCreate ? (
          <Button
            type="button"
            size="icon"
            className={cn(
              'h-10 w-10 shrink-0 rounded-full text-white',
              terrainBrandAction.bg,
              terrainBrandAction.hover,
              terrainBrandAction.shadow,
            )}
            aria-label="Créer un plan d’action"
            onClick={() => navigateTo('/action-plans/new')}
          >
            <Plus className="h-5 w-5" aria-hidden />
          </Button>
        ) : null}
      </div>

      <ActionPlanHubFilters
        establishmentId={establishmentId ?? ''}
        searchQuery={searchQuery}
        businessUnitId={businessUnitId}
        createdByMe={createdByMe}
        onSearchQueryChange={setSearchQuery}
        onBusinessUnitIdChange={setBusinessUnitId}
        onCreatedByMeChange={setCreatedByMe}
      />

      {useError ? <p className="text-sm text-destructive">{useError}</p> : null}

      {sections.length === 0 ? (
        <TerrainCard className="space-y-2 py-6 text-center">
          <p className="text-sm font-semibold text-[#1a1a1a]">Aucun plan trouvé</p>
          <p className={cn('text-xs leading-5', terrain.muted)}>
            {staffUseMode
              ? 'Aucun modèle actif disponible pour votre pôle.'
              : 'Ajustez les filtres ou créez un nouveau plan dans la bibliothèque.'}
          </p>
        </TerrainCard>
      ) : (
        <div className="space-y-6">
          {sections.map((section) => (
            <ActionPlanCatalogSectionView
              key={section.businessUnitId}
              section={section}
              isLoading={catalogQuery.isLoading}
              isError={catalogQuery.isError}
              onOpenPlan={(id) => navigateTo(`/action-plans/${id}`)}
              onUsePlan={setUsePlanId}
            />
          ))}
        </div>
      )}

      {usePlan ? (
        <ActionPlanUseSheet
          open={usePlanId != null}
          establishmentId={establishmentId ?? ''}
          pilotBusinessUnitId={usePlan.pilot_business_unit.id}
          isPending={useMutation.isPending || scheduleMutation.isPending}
          staffUseMode={staffUseMode}
          canSchedule={canShowActionPlanSchedule(usePlan.permission_hints)}
          onClose={() => setUsePlanId(null)}
          onPlanningSubmit={(result) => void handlePlanningSubmit(result)}
        />
      ) : null}
    </div>
  )
}
