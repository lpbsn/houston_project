import { useMutationState } from '@tanstack/react-query'
import { LoaderCircle } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainDetailTrailingSlot } from '@/components/layout/terrain-detail-trailing-slot'
import { Button } from '@/components/ui/button'
import { HoustonBadge, TerrainCard, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { getDisplayNameInitials } from '@/lib/display-names'
import { notifySuccess } from '@/lib/success-toast'
import { useLgViewport, useXlViewport } from '@/lib/lg-viewport'
import { terrain, terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanExecutionDetailLabel } from '../components/action-plan-execution-detail-label'
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
  ACTION_PLAN_DESKTOP_SCHEDULE_LABEL,
  ACTION_PLAN_DESKTOP_USE_LABEL,
  formatActionPlanSubmissionNotice,
  resolveDesktopLaunchLabel,
  summarizeCatalogPlanningLaunch,
} from '../lib/action-plan-desktop-form'
import {
  formatPlanningSubmitFeedback,
  isCatalogPlanningPrimaryDisabled,
  resolveCatalogPlanningSubmit,
  resolveCatalogPlanningSubmitFallbackMessage,
  validateCatalogPlanningDraft,
} from '../lib/action-plan-catalog-planning-submit'
import { formatActionPlanCreatedAtLabel, formatCatalogStatusLabel } from '../lib/action-plan-display'
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
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const placeDetailColumns = useXlViewport()
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
  const [hasAttemptedPlanningSubmit, setHasAttemptedPlanningSubmit] = useState(false)
  const [planningGuidanceNonce, setPlanningGuidanceNonce] = useState(0)
  const planningFormRootRef = useRef<HTMLDivElement>(null)
  const lastPlanningGuidanceNonceRef = useRef(0)
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )

  const planningFieldErrors = useMemo(
    () =>
      hasAttemptedPlanningSubmit && detailQuery.data
        ? validateCatalogPlanningDraft(planningDraft, {
            canSchedule: canShowActionPlanSchedule(detailQuery.data.permission_hints),
            staffMode: staffUseMode,
          })
        : {},
    [detailQuery.data, hasAttemptedPlanningSubmit, planningDraft, staffUseMode],
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
  const launchOutcome = summarizeCatalogPlanningLaunch(planningDraft, planningOptions)
  const launchLabel = resolveDesktopLaunchLabel(launchOutcome)
  const launchNotice = executionPanelOpen ? formatActionPlanSubmissionNotice(launchOutcome) : null

  function openExecutionPanel(schedule: boolean) {
    setPlanningDraft({
      ...createActionPlanEventPlanningDraft(),
      repeatEnabled: schedule && canSchedule,
    })
    setHasAttemptedPlanningSubmit(false)
    setExecutionPanelOpen(true)
  }

  const desktopActions =
    executionPanelOpen ? (
      <div className="flex min-w-0 flex-wrap items-center justify-end gap-2">
        {launchNotice ? (
          <p data-testid="action-plan-form-desktop-notice" className="text-sm text-[#555]">
            {launchNotice}
          </p>
        ) : null}
        <Button
          type="button"
          variant="outline"
          className="h-9 rounded-lg"
          disabled={isPrimaryPending}
          onClick={resetExecutionPanel}
        >
          Annuler
        </Button>
        <Button
          type="button"
          className={cn('h-9 rounded-lg px-4 text-white', terrainBrandAction.bg, terrainBrandAction.hover)}
          disabled={primaryActionDisabled}
          onClick={() => void handleLaunchExecution()}
        >
          {launchLabel}
        </Button>
      </div>
    ) : canUse ? (
      <div className="flex min-w-0 flex-wrap justify-end gap-2">
        <Button
          type="button"
          className={cn('h-9 rounded-lg px-4 text-white', terrainBrandAction.bg, terrainBrandAction.hover)}
          disabled={isBusy}
          onClick={() => openExecutionPanel(false)}
        >
          {ACTION_PLAN_DESKTOP_USE_LABEL}
        </Button>
        {canSchedule ? (
          <Button
            type="button"
            variant="outline"
            className="h-9 rounded-lg"
            disabled={isBusy}
            onClick={() => openExecutionPanel(true)}
          >
            {ACTION_PLAN_DESKTOP_SCHEDULE_LABEL}
          </Button>
        ) : null}
      </div>
    ) : null

  if (isDesktopWeb) {
    const catalogStatusLabel =
      plan.catalog_status === 'active' || plan.catalog_status === 'inactive'
        ? formatCatalogStatusLabel(plan.catalog_status)
        : null
    const statusActions =
      canShowActionPlanActivate(hints) || canShowActionPlanDeactivate(hints) ? (
        <div className="flex flex-col items-start gap-2 pt-2">
          {canShowActionPlanActivate(hints) ? (
            <Button
              type="button"
              variant="outline"
              className="h-8 rounded-full px-3 text-xs"
              disabled={activateMutation.isPending}
              onClick={() => void handleActivate()}
            >
              Activer
            </Button>
          ) : null}
          {canShowActionPlanDeactivate(hints) ? (
            <Button
              type="button"
              variant="outline"
              className="h-8 rounded-full px-3 text-xs text-[#E24B4A]"
              disabled={deactivateMutation.isPending}
              onClick={() => void handleDeactivate()}
            >
              Désactiver
            </Button>
          ) : null}
        </div>
      ) : null
    const titleCard = (
      <div data-testid="action-plan-desktop-title">
        <TerrainCard>
          <ActionPlanExecutionDetailLabel>Titre</ActionPlanExecutionDetailLabel>
          <h1 className="mt-2 text-[13px] font-normal leading-relaxed text-[#1a1a1a]">{plan.title}</h1>
        </TerrainCard>
      </div>
    )
    const descriptionCard = (
      <div data-testid="action-plan-desktop-description">
        <TerrainCard>
          <ActionPlanExecutionDetailLabel>Description</ActionPlanExecutionDetailLabel>
          <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-[#1a1a1a]">
            {plan.description.trim() || 'Aucune description.'}
          </p>
        </TerrainCard>
      </div>
    )
    const taskCard = (
      <section
        data-testid="action-plan-desktop-tasks"
        className="rounded-xl border border-[#E8E6DF] bg-[#FAFAF8] px-3 py-3"
      >
        <ActionPlanExecutionDetailLabel className="mb-2 text-[#7D7B75]">Tâches</ActionPlanExecutionDetailLabel>
        {sortedTasks.length === 0 ? (
          <p className={cn('text-[13px]', terrain.muted)}>Aucune tâche.</p>
        ) : (
          <div className="divide-y divide-[#E8E6DF]">
            {sortedTasks.map((task) => {
              const poleLabel = task.business_unit?.specific_name?.trim() ?? ''
              const taskDescription = task.description?.trim() ?? ''
              return (
                <div key={task.id} className="py-1.5">
                  <p className="break-words text-[13px] font-normal leading-snug text-[#1a1a1a]">
                    {task.task}
                  </p>
                  {poleLabel ? (
                    <p className="mt-0.5 break-words text-[11px] leading-snug text-[#9a958c]">
                      {poleLabel}
                    </p>
                  ) : null}
                  {taskDescription ? (
                    <p className="mt-0.5 break-words whitespace-pre-wrap text-[12px] leading-snug text-[#7D7B75]">
                      {taskDescription}
                    </p>
                  ) : null}
                </div>
              )
            })}
          </div>
        )}
      </section>
    )
    const sideColumn = (
      <div data-testid="action-plan-desktop-side" className="flex min-w-0 flex-col gap-4 self-start">
        <div data-testid="action-plan-desktop-organization">
        <TerrainCard className="space-y-3">
          <ActionPlanExecutionDetailLabel>Contexte</ActionPlanExecutionDetailLabel>
          {plan.requires_validation ? (
            <div>
              <HoustonBadge variant="gray" className="bg-[#F0EFE9] text-[10px] text-[#555]">
                Validation requise
              </HoustonBadge>
            </div>
          ) : null}
          <div className="space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
              Créateur
            </p>
            <p className="inline-flex max-w-full items-center gap-2 text-[13px] leading-relaxed text-[#1a1a1a]">
              <span
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#F0EFE9] text-[9px] font-bold text-[#5c564e]"
                aria-hidden
              >
                {getDisplayNameInitials(plan.created_by_display_name)}
              </span>
              <span className="min-w-0 break-words">{plan.created_by_display_name}</span>
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
              Pôle pilote
            </p>
            <p className="break-words text-[13px] leading-relaxed text-[#1a1a1a]">
              {plan.pilot_business_unit.specific_name}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
              Date de création
            </p>
            <p className="text-[13px] leading-relaxed text-[#1a1a1a]">
              {formatActionPlanCreatedAtLabel(plan.created_at)}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
              Dernière mise à jour
            </p>
            <p className="text-[13px] leading-relaxed text-[#1a1a1a]">
              {formatActionPlanCreatedAtLabel(plan.updated_at)}
            </p>
          </div>
          {catalogStatusLabel ? (
            <div className="space-y-1">
              <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
                État
              </p>
              <p className="text-[13px] leading-relaxed text-[#1a1a1a]">{catalogStatusLabel}</p>
              {statusActions}
            </div>
          ) : (
            statusActions
          )}
        </TerrainCard>
        </div>
        {executionPanelOpen ? (
          <div ref={planningFormRootRef}>
            <ActionPlanEventPlanningForm
              draft={planningDraft}
              layout="split"
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
    )

    return (
      <div
        data-testid="action-plan-template-detail-frame"
        className="mx-auto flex min-h-full w-full min-w-0 max-w-7xl flex-col px-6 pt-4 pb-8"
      >
        {desktopActions ? <TerrainDetailTrailingSlot>{desktopActions}</TerrainDetailTrailingSlot> : null}
        {displayedFeedback ? (
          <TerrainFeedback variant={displayedFeedback.variant} message={displayedFeedback.message} />
        ) : null}
        {placeDetailColumns ? (
          <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_20rem] items-start gap-5">
            <div data-testid="action-plan-desktop-main" className="flex min-w-0 flex-col gap-4">
              {titleCard}
              {descriptionCard}
              {taskCard}
            </div>
            {sideColumn}
          </div>
        ) : (
          <div className="flex min-w-0 flex-col gap-5">
            {titleCard}
            {descriptionCard}
            {sideColumn}
            {taskCard}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex min-h-full flex-col">
      <div
        data-testid="action-plan-template-detail-frame"
        className="flex min-h-full w-full flex-1 flex-col"
      >
        <div
          className={cn(
            'flex flex-col gap-3 px-3 pt-2',
            isDesktopWeb && 'lg:gap-4 lg:px-6 lg:pt-4',
            showStickyFooter ? 'pb-40' : 'pb-4',
            !showStickyFooter && isDesktopWeb && 'lg:pb-6',
          )}
        >
          {displayedFeedback ? (
            <div>
              <TerrainFeedback
                variant={displayedFeedback.variant}
                message={displayedFeedback.message}
              />
            </div>
          ) : null}

          <div className="space-y-3">
            <ActionPlanTemplateDetailHeader
              plan={plan}
              showActivate={canShowActionPlanActivate(hints)}
              showDeactivate={canShowActionPlanDeactivate(hints)}
              isActivatePending={activateMutation.isPending}
              isDeactivatePending={deactivateMutation.isPending}
              onActivate={() => void handleActivate()}
              onDeactivate={() => void handleDeactivate()}
            />
          </div>

          <div className="space-y-3">
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
          </div>

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
            className={isDesktopWeb ? 'lg:px-6' : undefined}
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
    </div>
  )
}
