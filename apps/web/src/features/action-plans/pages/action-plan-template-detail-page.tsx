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
  useUseActionPlanMutation,
} from '../hooks'
import { buildActionPlanUseRequest } from '../lib/action-plan-create-payload'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import {
  createActionPlanEventPlanningDraft,
  hasGlobalRepeat,
  shouldHidePrimaryPlanningActions,
  toScheduleDraft,
  toUseRequestOptions,
  validateActionPlanEventPlanningDraft,
  type ActionPlanAssigneeActionKind,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import {
  canShowActionPlanActivate,
  canShowActionPlanDeactivate,
  canShowActionPlanSchedule,
  canShowActionPlanUpdate,
  canShowActionPlanUse,
} from '../lib/action-plan-permission-hints'
import { buildActionPlanScheduleCreateRequest } from '../lib/action-plan-schedule-payload'
import { isActionPlanScheduleConfigured } from '../lib/action-plan-schedule-form'
import { isStaffActionPlanUsageRole } from '../lib/action-plan-management-access'
import type { ActionPlanScheduleCreateRequest, ActionPlanUseRequest } from '../types'

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

  const [executionPanelOpen, setExecutionPanelOpen] = useState(false)
  const [planningDraft, setPlanningDraft] = useState<ActionPlanEventPlanningDraft>(
    createActionPlanEventPlanningDraft,
  )
  const [planningFieldErrors, setPlanningFieldErrors] = useState<Record<string, string>>({})
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )
  const [assigneeActionPending, setAssigneeActionPending] = useState<
    Record<string, ActionPlanAssigneeActionKind>
  >({})

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
  const isRepeatSubmit = hasGlobalRepeat(planningDraft) && canSchedule
  const hidePrimaryAction = shouldHidePrimaryPlanningActions(planningDraft)
  const scheduleConfigured = isActionPlanScheduleConfigured(toScheduleDraft(planningDraft))
  const primaryActionLabel = isRepeatSubmit ? 'Planifier la récurrence' : "Lancer l'exécution"
  const isPrimaryPending = isRepeatSubmit ? scheduleMutation.isPending : useMutation.isPending
  const primaryActionDisabled =
    isRepeatSubmit ? !scheduleConfigured || isPrimaryPending : isPrimaryPending
  const isBusy =
    activateMutation.isPending ||
    deactivateMutation.isPending ||
    useMutation.isPending ||
    scheduleMutation.isPending

  const showStickyFooter =
    executionPanelOpen ||
    canUpdate ||
    canShowActionPlanActivate(hints) ||
    canShowActionPlanDeactivate(hints) ||
    canUse

  function resetExecutionPanel() {
    setExecutionPanelOpen(false)
    setPlanningDraft(createActionPlanEventPlanningDraft())
    setPlanningFieldErrors({})
    setAssigneeActionPending({})
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

  async function handleAssigneeSchedule(
    assigneeId: string,
    body: ActionPlanScheduleCreateRequest,
  ) {
    if (assigneeActionPending[assigneeId]) {
      return
    }
    setAssigneeActionPending((previous) => ({ ...previous, [assigneeId]: 'schedule' }))
    setFeedback(null)
    try {
      await scheduleMutation.mutateAsync(body)
      setFeedback({ variant: 'success', message: 'Récurrence assignée planifiée.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être planifié.'),
      })
    } finally {
      setAssigneeActionPending((previous) => {
        const next = { ...previous }
        delete next[assigneeId]
        return next
      })
    }
  }

  async function handleAssigneeLaunch(assigneeId: string, body: ActionPlanUseRequest) {
    if (assigneeActionPending[assigneeId]) {
      return
    }
    setAssigneeActionPending((previous) => ({ ...previous, [assigneeId]: 'launch' }))
    setFeedback(null)
    try {
      await useMutation.mutateAsync(body)
      setFeedback({ variant: 'success', message: 'Exécution assignée lancée.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être lancé.'),
      })
    } finally {
      setAssigneeActionPending((previous) => {
        const next = { ...previous }
        delete next[assigneeId]
        return next
      })
    }
  }

  async function handleLaunchExecution() {
    if (planningDraft.usePerAssigneeChronology) {
      return
    }

    const errors = validateActionPlanEventPlanningDraft(planningDraft, {
      requireAssignees: false,
      allowRepeat: canSchedule,
    })
    setPlanningFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }

    setFeedback(null)
    try {
      if (isRepeatSubmit) {
        const body = buildActionPlanScheduleCreateRequest({
          schedule: toScheduleDraft(planningDraft),
          assignees: staffUseMode ? [] : planningDraft.assignees,
          useSharedChronology: true,
        })
        if (!body) {
          return
        }
        await scheduleMutation.mutateAsync(body)
        resetExecutionPanel()
        setFeedback({ variant: 'success', message: 'Récurrence planifiée.' })
        return
      }

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
        message: resolveActionPlanErrorMessage(
          error,
          isRepeatSubmit ? 'Le plan n’a pas pu être planifié.' : 'Le plan n’a pas pu être lancé.',
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
              assigneeActionPending,
            }}
            establishmentId={establishmentId}
            pilotBusinessUnitId={plan.pilot_business_unit.id}
            fieldErrors={planningFieldErrors}
            onDraftChange={setPlanningDraft}
            onAssigneeSchedule={(assigneeId, body) =>
              void handleAssigneeSchedule(assigneeId, body)
            }
            onAssigneeLaunch={(assigneeId, body) => void handleAssigneeLaunch(assigneeId, body)}
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
          primaryActionLabel={primaryActionLabel}
          primaryActionDisabled={primaryActionDisabled}
          isPrimaryPending={isPrimaryPending}
          hidePrimaryAction={hidePrimaryAction}
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
