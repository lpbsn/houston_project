import { LoaderCircle, Plus } from 'lucide-react'
import { useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState, TerrainSectionLabel, TerrainStickyFooter } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanEventPlanningForm } from '../components/action-plan-event-planning-form'
import { ActionPlanTaskReadOnlyRow } from '../components/action-plan-task-read-only-row'
import { ActionPlanTemplateDetailHeader } from '../components/action-plan-template-detail-header'
import {
  useActivateActionPlanMutation,
  useActionPlanDetailQuery,
  useDeactivateActionPlanMutation,
  useUseActionPlanMutation,
} from '../hooks'
import { buildActionPlanUseRequest } from '../lib/action-plan-create-payload'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import {
  createActionPlanEventPlanningDraft,
  toUseRequestOptions,
  validateActionPlanEventPlanningDraft,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import {
  canShowActionPlanActivate,
  canShowActionPlanDeactivate,
  canShowActionPlanUpdate,
  canShowActionPlanUse,
} from '../lib/action-plan-permission-hints'
import { isStaffActionPlanUsageRole } from '../lib/action-plan-management-access'

type ActionPlanTemplateDetailPageProps = {
  actionPlanId: string
}

export function ActionPlanTemplateDetailPage({ actionPlanId }: ActionPlanTemplateDetailPageProps) {
  const { navigate } = useAppRoute()
  const { activeMembership, bootstrap } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null
  const staffUseMode = isStaffActionPlanUsageRole(activeMembership?.role ?? null)
  const staffDisplayName = bootstrap?.user?.username ?? 'Moi'

  const detailQuery = useActionPlanDetailQuery(establishmentId, actionPlanId)
  const activateMutation = useActivateActionPlanMutation(establishmentId ?? '', actionPlanId)
  const deactivateMutation = useDeactivateActionPlanMutation(establishmentId ?? '', actionPlanId)
  const useMutation = useUseActionPlanMutation(establishmentId ?? '', actionPlanId)

  const [executionPanelOpen, setExecutionPanelOpen] = useState(false)
  const [planningDraft, setPlanningDraft] = useState<ActionPlanEventPlanningDraft>(
    createActionPlanEventPlanningDraft,
  )
  const [planningFieldErrors, setPlanningFieldErrors] = useState<Record<string, string>>({})
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )

  if (!establishmentId) {
    return null
  }

  if (detailQuery.isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 px-3 py-10 text-sm text-[#7D7B75]">
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
        Chargement du plan...
      </div>
    )
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message={resolveActionPlanErrorMessage(
          detailQuery.error,
          'Ce plan est introuvable ou inaccessible.',
        )}
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  const plan = detailQuery.data
  const hints = plan.permission_hints
  const canUpdate = canShowActionPlanUpdate(hints)
  const canUse = canShowActionPlanUse(hints)
  const isBusy =
    activateMutation.isPending || deactivateMutation.isPending || useMutation.isPending

  function resetExecutionPanel() {
    setExecutionPanelOpen(false)
    setPlanningDraft(createActionPlanEventPlanningDraft())
    setPlanningFieldErrors({})
  }

  async function handleActivate() {
    setFeedback(null)
    try {
      await activateMutation.mutateAsync()
      setFeedback({ variant: 'success', message: 'Plan activé dans la bibliothèque.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être activé.'),
      })
    }
  }

  async function handleDeactivate() {
    setFeedback(null)
    try {
      await deactivateMutation.mutateAsync()
      setFeedback({ variant: 'success', message: 'Plan désactivé.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être désactivé.'),
      })
    }
  }

  async function handleLaunchExecution() {
    const errors = validateActionPlanEventPlanningDraft(planningDraft, {
      requireAssignees: false,
      allowRepeat: false,
    })
    setPlanningFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }

    setFeedback(null)
    try {
      const useOptions = toUseRequestOptions(planningDraft)
      const execution = await useMutation.mutateAsync(
        buildActionPlanUseRequest({
          ...useOptions,
          assignees: staffUseMode ? [] : useOptions.assignees,
        }),
      )
      resetExecutionPanel()
      navigate(`/action-plans/executions/${execution.id}`)
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être lancé.'),
      })
    }
  }

  const sortedTasks = [...plan.tasks].sort((left, right) => left.position - right.position)

  return (
    <div className="flex min-h-full flex-col">
      <div className={cn('space-y-3 px-3 pt-2', executionPanelOpen ? 'pb-28' : 'pb-6')}>
        {feedback ? <TerrainFeedback variant={feedback.variant} message={feedback.message} /> : null}

        <ActionPlanTemplateDetailHeader plan={plan} />

        <section className="space-y-2">
          <TerrainSectionLabel>Tâches</TerrainSectionLabel>
          {sortedTasks.length === 0 ? (
            <TerrainCard className="p-0">
              <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Aucune tâche.</p>
            </TerrainCard>
          ) : (
            <div className="space-y-1">
              {sortedTasks.map((task) => (
                <TerrainCard key={task.id} className="p-0">
                  <ActionPlanTaskReadOnlyRow task={task} />
                </TerrainCard>
              ))}
            </div>
          )}
        </section>

        <div className="flex flex-col gap-2">
          {canUpdate ? (
            <Button
              type="button"
              variant="outline"
              className="h-11 w-full rounded-xl"
              disabled={isBusy}
              onClick={() => navigate(`/action-plans/${actionPlanId}/edit`)}
            >
              Modifier
            </Button>
          ) : null}
          {canShowActionPlanActivate(hints) ? (
            <Button
              type="button"
              variant="outline"
              className="h-11 w-full rounded-xl"
              disabled={isBusy}
              onClick={() => void handleActivate()}
            >
              Activer dans la bibliothèque
            </Button>
          ) : null}
          {canShowActionPlanDeactivate(hints) ? (
            <Button
              type="button"
              variant="outline"
              className="h-11 w-full rounded-xl text-[#E24B4A]"
              disabled={isBusy}
              onClick={() => void handleDeactivate()}
            >
              Désactiver
            </Button>
          ) : null}
        </div>

        {executionPanelOpen ? (
          <ActionPlanEventPlanningForm
            draft={planningDraft}
            config={{
              canEditAssignees: !staffUseMode,
              canSchedule: false,
              staffMode: staffUseMode,
              showAdvancedChronology: !staffUseMode,
              hideAssignees: false,
              staffDisplayName,
            }}
            establishmentId={establishmentId}
            pilotBusinessUnitId={plan.pilot_business_unit.id}
            fieldErrors={planningFieldErrors}
            onDraftChange={setPlanningDraft}
          />
        ) : null}

        {canUse && !executionPanelOpen ? (
          <Button
            type="button"
            className="h-11 w-full rounded-xl"
            disabled={isBusy}
            onClick={() => setExecutionPanelOpen(true)}
          >
            <Plus className="mr-2 h-4 w-4" aria-hidden />
            Exécution
          </Button>
        ) : null}
      </div>

      {executionPanelOpen ? (
        <TerrainStickyFooter>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              className="h-11 flex-1 rounded-xl"
              disabled={useMutation.isPending}
              onClick={resetExecutionPanel}
            >
              Annuler
            </Button>
            <Button
              type="button"
              className="h-11 flex-1 rounded-xl"
              disabled={useMutation.isPending}
              onClick={() => void handleLaunchExecution()}
            >
              Lancer l&apos;exécution
            </Button>
          </div>
        </TerrainStickyFooter>
      ) : null}
    </div>
  )
}
