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
import { terrain } from '@/lib/terrain-styles'
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
import type { ActionPlanScheduleCreateRequest, ActionPlanUseRequest, ActionPlanCatalogListFilters } from '../types'

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

  async function handleSchedule(body: Parameters<typeof scheduleMutation.mutateAsync>[0]['body']) {
    if (!usePlanId) {
      return
    }
    setUseError(null)
    try {
      await scheduleMutation.mutateAsync({ actionPlanId: usePlanId, body })
      setUsePlanId(null)
    } catch (error) {
      setUseError(resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être planifié.'))
    }
  }

  async function handleUse(body: Parameters<typeof useMutation.mutateAsync>[0]['body']) {
    if (!usePlanId) {
      return
    }
    setUseError(null)
    try {
      const execution = await useMutation.mutateAsync({ actionPlanId: usePlanId, body })
      setUsePlanId(null)
      navigateTo(`/action-plans/executions/${execution.id}`)
    } catch (error) {
      setUseError(resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être utilisé.'))
    }
  }

  async function handleAssigneeSchedule(
    _assigneeId: string,
    body: ActionPlanScheduleCreateRequest,
  ) {
    await handleSchedule(body)
  }

  async function handleAssigneeLaunch(_assigneeId: string, body: ActionPlanUseRequest) {
    await handleUse(body)
  }

  return (
    <div className="space-y-3 px-3 pb-24 pt-2">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className={cn('text-sm', terrain.muted)}>Bibliothèque de plans d&apos;action</p>
          <p className="text-xs text-[#7D7B75]">
            Réutilisez des modèles validés pour lancer des exécutions.
          </p>
        </div>
        {canCreate ? (
          <Button
            type="button"
            size="icon"
            className="h-11 w-11 shrink-0 rounded-xl"
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
        sections.map((section) => (
          <ActionPlanCatalogSectionView
            key={section.businessUnitId}
            section={section}
            isLoading={catalogQuery.isLoading}
            isError={catalogQuery.isError}
            onOpenPlan={(id) => navigateTo(`/action-plans/${id}`)}
            onUsePlan={setUsePlanId}
          />
        ))
      )}

      {usePlan ? (
        <ActionPlanUseSheet
          open={usePlanId != null}
          establishmentId={establishmentId ?? ''}
          pilotBusinessUnitId={usePlan.pilot_business_unit.id}
          isPending={useMutation.isPending}
          isSchedulePending={scheduleMutation.isPending}
          staffUseMode={staffUseMode}
          canSchedule={canShowActionPlanSchedule(usePlan.permission_hints)}
          onClose={() => setUsePlanId(null)}
          onConfirm={(body) => void handleUse(body)}
          onScheduleConfirm={(body) => void handleSchedule(body)}
          onAssigneeSchedule={(assigneeId, body) => void handleAssigneeSchedule(assigneeId, body)}
          onAssigneeLaunch={(assigneeId, body) => void handleAssigneeLaunch(assigneeId, body)}
        />
      ) : null}
    </div>
  )
}
