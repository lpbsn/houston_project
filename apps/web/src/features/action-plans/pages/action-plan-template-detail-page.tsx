import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanEventPlanningForm } from '../components/action-plan-event-planning-form'
import { ActionPlanTaskReadOnlyRow } from '../components/action-plan-task-read-only-row'
import { ActionPlanTemplateDetailHeader } from '../components/action-plan-template-detail-header'
import { ActionPlanTemplateDetailStickyFooter } from '../components/action-plan-template-detail-sticky-footer'
import {
  useActivateActionPlanMutation,
  useActionPlanDetailQuery,
  useCreateActionPlanScheduleMutation,
  useDeactivateActionPlanMutation,
  useSubmitMixedActionPlanFromCatalogMutation,
  useUseActionPlanMutation,
} from '../hooks'
import {
  isCatalogPlanningPrimaryDisabled,
  resolveCatalogPlanningSubmit,
  resolveCatalogPlanningSubmitFallbackMessage,
  validateCatalogPlanningDraft,
} from '../lib/action-plan-catalog-planning-submit'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import {
  clearMixedSubmissionIntent,
  resolveMixedSubmissionIntent,
} from '../lib/action-plan-mixed-submission-intent'
import {
  createActionPlanEventPlanningDraft,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import {
  canShowActionPlanActivate,
  canShowActionPlanDeactivate,
  canShowActionPlanSchedule,
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
  const scheduleMutation = useCreateActionPlanScheduleMutation(establishmentId ?? '', actionPlanId)
  const mixedMutation = useSubmitMixedActionPlanFromCatalogMutation(establishmentId ?? '')

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
  const canSchedule = canShowActionPlanSchedule(hints)
  const planningOptions = { canSchedule, staffMode: staffUseMode }
  const isPrimaryPending = useMutation.isPending || scheduleMutation.isPending
  const primaryActionDisabled = isCatalogPlanningPrimaryDisabled(planningDraft, {
    ...planningOptions,
    isPending: isPrimaryPending,
  })
  const isBusy =
    activateMutation.isPending ||
    deactivateMutation.isPending ||
    useMutation.isPending ||
    scheduleMutation.isPending ||
    mixedMutation.isPending

  const showStickyFooter =
    executionPanelOpen ||
    canUpdate ||
    canShowActionPlanActivate(hints) ||
    canShowActionPlanDeactivate(hints) ||
    canUse

  function resetExecutionPanel() {
    clearMixedSubmissionIntent(establishmentId, actionPlanId)
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
    const errors = validateCatalogPlanningDraft(planningDraft, planningOptions)
    setPlanningFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }

    const submit = resolveCatalogPlanningSubmit(planningDraft, planningOptions)
    if (!submit) {
      return
    }

    setFeedback(null)
    try {
      if (submit.kind === 'schedule') {
        await scheduleMutation.mutateAsync(submit.scheduleBody)
        resetExecutionPanel()
        setFeedback({ variant: 'success', message: 'Récurrence planifiée.' })
        return
      }

      if (submit.kind === 'mixed') {
        const intent = await resolveMixedSubmissionIntent({
          establishmentId,
          actionPlanId,
          scheduleBody: submit.scheduleBody,
          useBody: submit.useBody,
        })
        const response = await mixedMutation.mutateAsync({
          actionPlanId,
          body: {
            submission_id: intent.submissionId,
            schedule_body: submit.scheduleBody,
            use_body: submit.useBody,
          },
        })
        resetExecutionPanel()
        navigate(`/action-plans/executions/${response.execution.id}`)
        return
      }

      const execution = await useMutation.mutateAsync(submit.useBody)
      resetExecutionPanel()
      navigate(`/action-plans/executions/${execution.id}`)
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(
          error,
          resolveCatalogPlanningSubmitFallbackMessage(submit, error),
        ),
      })
    }
  }

  const sortedTasks = [...plan.tasks].sort((left, right) => left.position - right.position)

  return (
    <div className="flex min-h-full flex-col">
      <div
        className={cn(
          'flex flex-1 flex-col gap-3 px-3 pt-2',
          showStickyFooter ? 'pb-40' : 'pb-4',
        )}
      >
        {feedback ? (
          <TerrainFeedback variant={feedback.variant} message={feedback.message} />
        ) : null}

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

        {executionPanelOpen ? (
          <ActionPlanEventPlanningForm
            draft={planningDraft}
            config={{
              canEditAssignees: !staffUseMode,
              canSchedule,
              staffMode: staffUseMode,
              showAdvancedChronology: !staffUseMode,
              hideAssignees: false,
              staffDisplayName,
              assigneeActionsEnabled: false,
            }}
            establishmentId={establishmentId}
            pilotBusinessUnitId={plan.pilot_business_unit.id}
            fieldErrors={planningFieldErrors}
            onDraftChange={setPlanningDraft}
          />
        ) : null}
      </div>

      {showStickyFooter ? (
        <ActionPlanTemplateDetailStickyFooter
          hints={hints}
          executionPanelOpen={executionPanelOpen}
          canUpdate={canUpdate}
          canUse={canUse}
          isBusy={isBusy}
          primaryActionDisabled={primaryActionDisabled}
          isPrimaryPending={isPrimaryPending}
          onNavigateToEdit={() => navigate(`/action-plans/${actionPlanId}/edit`)}
          onActivate={() => void handleActivate()}
          onDeactivate={() => void handleDeactivate()}
          onOpenExecutionPanel={() => setExecutionPanelOpen(true)}
          onCloseExecutionPanel={resetExecutionPanel}
          onLaunchExecution={() => void handleLaunchExecution()}
        />
      ) : null}
    </div>
  )
}
