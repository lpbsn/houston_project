import { useMutationState } from '@tanstack/react-query'
import { LoaderCircle } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { notifySuccess } from '@/lib/success-toast'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanEventPlanningForm } from '../components/action-plan-event-planning-form'
import { ActionPlanTaskReadOnlyRow } from '../components/action-plan-task-read-only-row'
import { ActionPlanTemplateDetailHeader } from '../components/action-plan-template-detail-header'
import { ActionPlanTemplateDetailStickyFooter } from '../components/action-plan-template-detail-sticky-footer'
import {
  deleteActionPlanMutationKey,
  useActivateActionPlanMutation,
  useActionPlanDetailQuery,
  useDeactivateActionPlanMutation,
  useSubmitActionPlanPlanningMutation,
} from '../hooks'
import {
  formatPlanningSubmitFeedback,
  isCatalogPlanningPrimaryDisabled,
  resolveCatalogPlanningSubmit,
  resolveCatalogPlanningSubmitFallbackMessage,
  validateCatalogPlanningDraft,
} from '../lib/action-plan-catalog-planning-submit'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import { guideToFirstActionPlanFieldError } from '../lib/action-plan-form-guidance'
import {
  applyPlanningSubmissionIntent,
  clearPlanningSubmissionIntent,
  resolvePlanningSubmissionIntent,
} from '../lib/action-plan-planning-submission-intent'
import {
  createActionPlanEventPlanningDraft,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import {
  canShowActionPlanActivate,
  canShowActionPlanDeactivate,
  canShowActionPlanSchedule,
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
  const planningMutation = useSubmitActionPlanPlanningMutation(establishmentId ?? '')
  const deleteMutationErrors = useMutationState({
    filters: {
      mutationKey: deleteActionPlanMutationKey(establishmentId ?? '', actionPlanId),
      status: 'error',
    },
    select: (mutation) => mutation.state.error,
  })
  const latestDeleteError = deleteMutationErrors.at(-1) ?? null

  const [executionPanelOpen, setExecutionPanelOpen] = useState(false)
  const [planningDraft, setPlanningDraft] = useState<ActionPlanEventPlanningDraft>(
    createActionPlanEventPlanningDraft,
  )
  const [planningFieldErrors, setPlanningFieldErrors] = useState<Record<string, string>>({})
  const [hasAttemptedPlanningSubmit, setHasAttemptedPlanningSubmit] = useState(false)
  const [planningGuidanceNonce, setPlanningGuidanceNonce] = useState(0)
  const planningFormRootRef = useRef<HTMLDivElement>(null)
  const lastPlanningGuidanceNonceRef = useRef(0)
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )

  useEffect(() => {
    if (planningGuidanceNonce <= lastPlanningGuidanceNonceRef.current) {
      return
    }
    lastPlanningGuidanceNonceRef.current = planningGuidanceNonce
    if (Object.keys(planningFieldErrors).length === 0) {
      return
    }
    return guideToFirstActionPlanFieldError(planningFieldErrors, {
      root: planningFormRootRef.current ?? document,
    })
  }, [planningFieldErrors, planningGuidanceNonce])

  useEffect(() => {
    if (!hasAttemptedPlanningSubmit || !detailQuery.data) {
      return
    }
    setPlanningFieldErrors(
      validateCatalogPlanningDraft(planningDraft, {
        canSchedule: canShowActionPlanSchedule(detailQuery.data.permission_hints),
        staffMode: staffUseMode,
      }),
    )
  }, [detailQuery.data, hasAttemptedPlanningSubmit, planningDraft, staffUseMode])

  const displayedFeedback =
    feedback ??
    (latestDeleteError
      ? {
          variant: 'error' as const,
          message: resolveActionPlanErrorMessage(
            latestDeleteError,
            'Le modèle n’a pas pu être supprimé.',
          ),
        }
      : null)

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
  const canUse = canShowActionPlanUse(hints)
  const canSchedule = canShowActionPlanSchedule(hints)
  const planningOptions = { canSchedule, staffMode: staffUseMode }
  const isPrimaryPending = planningMutation.isPending
  const primaryActionDisabled = isCatalogPlanningPrimaryDisabled(planningDraft, {
    ...planningOptions,
    isPending: isPrimaryPending,
  })
  const isBusy =
    activateMutation.isPending ||
    deactivateMutation.isPending ||
    planningMutation.isPending

  const showStickyFooter = executionPanelOpen || canUse

  function resetExecutionPanel() {
    clearPlanningSubmissionIntent(establishmentId, actionPlanId)
    setExecutionPanelOpen(false)
    setPlanningDraft(createActionPlanEventPlanningDraft())
    setPlanningFieldErrors({})
    setHasAttemptedPlanningSubmit(false)
  }

  async function handleActivate() {
    setFeedback(null)
    try {
      await activateMutation.mutateAsync()
      notifySuccess({ message: 'Modèle activé.', kind: 'activated' })
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
      notifySuccess({ message: 'Modèle désactivé.', kind: 'deactivated' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être désactivé.'),
      })
    }
  }

  async function handleLaunchExecution() {
    setHasAttemptedPlanningSubmit(true)
    const errors = validateCatalogPlanningDraft(planningDraft, planningOptions)
    setPlanningFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      setPlanningGuidanceNonce((value) => value + 1)
      return
    }

    const submit = resolveCatalogPlanningSubmit(planningDraft, planningOptions)
    if (!submit) {
      return
    }

    setFeedback(null)
    try {
      const intent = await resolvePlanningSubmissionIntent({
        establishmentId,
        actionPlanId,
        body: {
          use_shared_chronology: submit.body.use_shared_chronology,
          items: submit.body.items,
        },
      })
      const response = await planningMutation.mutateAsync({
        actionPlanId,
        body: applyPlanningSubmissionIntent(
          {
            use_shared_chronology: submit.body.use_shared_chronology,
            items: submit.body.items,
          },
          intent,
        ),
      })
      clearPlanningSubmissionIntent(establishmentId, actionPlanId)
      resetExecutionPanel()
      notifySuccess({
        message: formatPlanningSubmitFeedback(response.summary),
        kind: 'created',
      })
      navigate('/execution')
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
        {displayedFeedback ? (
          <TerrainFeedback
            variant={displayedFeedback.variant}
            message={displayedFeedback.message}
          />
        ) : null}

        <ActionPlanTemplateDetailHeader
          plan={plan}
          showActivate={canShowActionPlanActivate(hints)}
          showDeactivate={canShowActionPlanDeactivate(hints)}
          isActivatePending={activateMutation.isPending}
          isDeactivatePending={deactivateMutation.isPending}
          onActivate={() => void handleActivate()}
          onDeactivate={() => void handleDeactivate()}
        />

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
          <div ref={planningFormRootRef}>
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
              onDraftChange={(update) => {
                setPlanningDraft((previous) =>
                  typeof update === 'function' ? update(previous) : update,
                )
              }}
            />
          </div>
        ) : null}
      </div>

      {showStickyFooter ? (
        <ActionPlanTemplateDetailStickyFooter
          hints={hints}
          executionPanelOpen={executionPanelOpen}
          canUse={canUse}
          isBusy={isBusy}
          primaryActionDisabled={primaryActionDisabled}
          isPrimaryPending={isPrimaryPending}
          onOpenExecutionPanel={() => setExecutionPanelOpen(true)}
          onCloseExecutionPanel={resetExecutionPanel}
          onLaunchExecution={() => void handleLaunchExecution()}
        />
      ) : null}
    </div>
  )
}
