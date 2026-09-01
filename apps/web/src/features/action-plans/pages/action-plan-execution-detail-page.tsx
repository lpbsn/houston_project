import { LoaderCircle } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { serializeScopedSignalDetailPath } from '@/app/scoped-terrain'
import { useAuth } from '@/app/auth-provider'
import { TerrainEmptyState, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import {
  ActionDetailTabs,
  type ActionDetailTab,
} from '@/features/action-plans/components/action-detail-tabs'
import { ActionLinkedSignalCard } from '@/features/action-plans/components/action-linked-signal-card'
import { ActionLinkedSignalStrip } from '@/features/action-plans/components/action-linked-signal-strip'
import { CommentSection } from '@/features/comments/components/comment-section'
import {
  buildAnalyticsSignalDetailPath,
  parseAnalyticsSignalReturnContext,
} from '@/features/analytics/lib/analytics-url-state'
import { parseDetailDeepLink } from '@/features/comments/lib/detail-deep-link'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { trackObservation } from '@/features/observations/components/observation-processing-tracker-provider'
import { useTaskObservationComposeDraft } from '@/features/observations/lib/use-observation-compose-draft'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { useNetworkStatus } from '@/lib/network-status'
import { notifySuccess } from '@/lib/success-toast'
import { cn } from '@/lib/utils'

import { ActionPlansApiError } from '../api'
import { ActionPlanExecutionDetailHeader } from '../components/action-plan-execution-detail-header'
import { ActionPlanExecutionDetailPoleSummarySection } from '../components/action-plan-execution-detail-pole-summary-section'
import { ActionPlanExecutionObservationSheet } from '../components/action-plan-execution-observation-sheet'
import { ActionPlanExecutionSkipSheet } from '../components/action-plan-execution-skip-sheet'
import {
  ActionPlanExecutionTaskActionsSheet,
  type ActionPlanTaskActionId,
} from '../components/action-plan-execution-task-actions-sheet'
import { ActionPlanExecutionValidateRatingSheet } from '../components/action-plan-execution-validate-rating-sheet'
import { ActionPlanExecutionStickyFooter } from '../components/action-plan-execution-sticky-footer'
import { ActionPlanExecutionTaskFilters } from '../components/action-plan-execution-task-filters'
import { ActionPlanExecutionTaskList } from '../components/action-plan-execution-task-list'
import {
  useCancelActionPlanExecutionMutation,
  useCreateObservationFromActionPlanTaskMutation,
  useMarkActionPlanExecutionDoneMutation,
  useMarkActionPlanTaskDoneMutation,
  useMarkActionPlanTaskPendingMutation,
  useReopenActionPlanExecutionMutation,
  useSkipActionPlanTaskMutation,
  useValidateActionPlanExecutionMutation,
  useActionPlanExecutionDetailQuery,
} from '../hooks'
import {
  buildActionPlanPoleTaskSummaries,
  isActionPlanExecutionOverdue,
  isActionPlanExecutionTerminal,
} from '../lib/action-plan-display'
import { filterActionPlanTasksByPole } from '../lib/filter-action-plan-tasks-by-pole'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import { resolveMarkActionPlanExecutionDoneSuccess } from '../lib/action-plan-lifecycle-success-messages'
import {
  canShowActionPlanExecutionCancel,
} from '../lib/action-plan-permission-hints'
import type { ActionPlanExecutionDetail, ActionPlanTaskExecution } from '../types'

type ActionPlanExecutionDetailPageProps = {
  executionId: string
  establishmentId?: string | null
  source?: 'establishment' | 'cross'
}

type ActionPlanExecutionDetailPageContentProps = {
  executionId: string
  establishmentId: string
  execution: ActionPlanExecutionDetail
  source: 'establishment' | 'cross'
}

function ActionPlanExecutionDetailPageContent({
  executionId,
  establishmentId,
  execution,
  source,
}: ActionPlanExecutionDetailPageContentProps) {
  const { navigate, search: locationSearch } = useAppRoute()
  const { activeMembership } = useAuth()
  const { isOnline } = useNetworkStatus()
  const markDoneMutation = useMarkActionPlanExecutionDoneMutation(establishmentId, executionId)
  const validateMutation = useValidateActionPlanExecutionMutation(establishmentId, executionId)
  const reopenMutation = useReopenActionPlanExecutionMutation(establishmentId, executionId)
  const cancelMutation = useCancelActionPlanExecutionMutation(establishmentId, executionId)
  const markTaskDoneMutation = useMarkActionPlanTaskDoneMutation(establishmentId, executionId)
  const markTaskPendingMutation = useMarkActionPlanTaskPendingMutation(establishmentId, executionId)
  const skipMutation = useSkipActionPlanTaskMutation(establishmentId, executionId)
  const observationMutation = useCreateObservationFromActionPlanTaskMutation(
    establishmentId,
    executionId,
  )

  const initialDeepLink = parseDetailDeepLink(locationSearch)
  const validationActionsRef = useRef<HTMLDivElement | null>(null)
  const [activeTab, setActiveTab] = useState<ActionDetailTab>(
    initialDeepLink.tab === 'comments' ? 'comments' : 'details',
  )
  const [hasOpenedComments, setHasOpenedComments] = useState(initialDeepLink.tab === 'comments')
  const highlightCommentId = initialDeepLink.commentId
  const shouldFocusValidation = parseDetailDeepLink(locationSearch).focus === 'validation'
  const [dismissedFocusValidationSearch, setDismissedFocusValidationSearch] = useState<string | null>(
    null,
  )
  const [previousShouldFocusValidation, setPreviousShouldFocusValidation] =
    useState(shouldFocusValidation)

  if (shouldFocusValidation !== previousShouldFocusValidation) {
    setPreviousShouldFocusValidation(shouldFocusValidation)
    if (shouldFocusValidation) {
      setDismissedFocusValidationSearch(null)
    }
  }

  const resolvedActiveTab: ActionDetailTab =
    shouldFocusValidation && locationSearch !== dismissedFocusValidationSearch
      ? 'details'
      : activeTab
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )
  const [skipTaskId, setSkipTaskId] = useState<string | null>(null)
  const [taskActionsTask, setTaskActionsTask] = useState<ActionPlanTaskExecution | null>(null)
  const [observationTaskId, setObservationTaskId] = useState<string | null>(null)
  const observationDraft = useTaskObservationComposeDraft(establishmentId, observationTaskId)
  const [validationStars, setValidationStars] = useState<number | null>(null)
  const [validationComment, setValidationComment] = useState('')
  const [isValidationSheetOpen, setIsValidationSheetOpen] = useState(false)
  const [selectedPoleId, setSelectedPoleId] = useState<string | null>(null)

  const poleSummaries = useMemo(
    () => buildActionPlanPoleTaskSummaries(execution),
    [execution],
  )
  const filteredTasks = useMemo(
    () => filterActionPlanTasksByPole(execution.task_executions, selectedPoleId),
    [execution.task_executions, selectedPoleId],
  )

  const isMutationPending =
    markDoneMutation.isPending ||
    validateMutation.isPending ||
    reopenMutation.isPending ||
    cancelMutation.isPending ||
    markTaskDoneMutation.isPending ||
    markTaskPendingMutation.isPending ||
    skipMutation.isPending ||
    observationMutation.isPending

  const isTerminal = isActionPlanExecutionTerminal(execution.status)
  const isOverdue = isActionPlanExecutionOverdue(execution.end_at, isTerminal)
  const permissionHints = execution.permission_hints
  const signalSummary = execution.signal_summary
  const analyticsSignalReturnContext = useMemo(
    () => parseAnalyticsSignalReturnContext(locationSearch, { now: new Date() }),
    [locationSearch],
  )
  const signalSummaryPath =
    signalSummary && analyticsSignalReturnContext
      ? buildAnalyticsSignalDetailPath(signalSummary.id, {
          patternId: analyticsSignalReturnContext.patternId,
          state: analyticsSignalReturnContext.state,
        })
      : signalSummary && source === 'cross'
        ? serializeScopedSignalDetailPath({ type: 'cross' }, signalSummary.id)
        : signalSummary
          ? `/signals/${signalSummary.id}`
          : null
  const canShowLifecycleFooter =
    permissionHints.can_mark_done ||
    permissionHints.can_validate ||
    permissionHints.can_reopen ||
    canShowActionPlanExecutionCancel(permissionHints, { isTerminal })
  const showStickyFooter = resolvedActiveTab === 'details' && canShowLifecycleFooter
  const shouldScrollToValidationActions =
    shouldFocusValidation && resolvedActiveTab === 'details' && permissionHints.can_validate

  useEffect(() => {
    if (!shouldScrollToValidationActions) {
      return
    }

    validationActionsRef.current?.scrollIntoView({ block: 'end' })
  }, [shouldScrollToValidationActions])

  const mutationError =
    markDoneMutation.error ??
    validateMutation.error ??
    reopenMutation.error ??
    cancelMutation.error ??
    null

  const handleTabChange = (tab: ActionDetailTab) => {
    if (shouldFocusValidation) {
      setDismissedFocusValidationSearch(locationSearch)
    }
    if (tab === 'comments') {
      setHasOpenedComments(true)
    }
    setActiveTab(tab)
  }

  async function handleMarkDone() {
    setFeedback(null)
    try {
      const result = await markDoneMutation.mutateAsync()
      notifySuccess(resolveMarkActionPlanExecutionDoneSuccess(result.status))
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être marqué terminé.'),
      })
    }
  }

  async function handleValidate() {
    setIsValidationSheetOpen(true)
  }

  async function handleValidateConfirm() {
    setFeedback(null)
    try {
      if (validationStars == null) {
        return
      }
      await validateMutation.mutateAsync({
        stars: validationStars,
        comment: validationComment,
      })
      setIsValidationSheetOpen(false)
      setValidationStars(null)
      setValidationComment('')
      notifySuccess({ message: 'Plan validé.', kind: 'validated' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être validé.'),
      })
    }
  }

  async function handleReopen() {
    setFeedback(null)
    try {
      await reopenMutation.mutateAsync()
      notifySuccess({ message: 'Plan rouvert.', kind: 'reopened' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être rouvert.'),
      })
    }
  }

  async function handleCancel() {
    setFeedback(null)
    try {
      await cancelMutation.mutateAsync()
      notifySuccess({ message: 'Plan annulé.', kind: 'canceled' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être annulé.'),
      })
    }
  }

  async function handleTaskMarkDone(taskExecutionId: string) {
    setFeedback(null)
    try {
      await markTaskDoneMutation.mutateAsync(taskExecutionId)
      setFeedback({ variant: 'success', message: 'Tâche terminée.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'La tâche n’a pas pu être terminée.'),
      })
    }
  }

  async function handleTaskMarkPending(taskExecutionId: string) {
    setFeedback(null)
    try {
      await markTaskPendingMutation.mutateAsync(taskExecutionId)
      setFeedback({ variant: 'success', message: 'Tâche remise en cours.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'La tâche n’a pas pu être remise en cours.'),
      })
    }
  }

  async function handleSkip(taskExecutionId: string) {
    setFeedback(null)
    try {
      await skipMutation.mutateAsync({
        taskExecutionId,
        body: {},
      })
      setSkipTaskId(null)
      setFeedback({ variant: 'success', message: 'Tâche passée.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'La tâche n’a pas pu être passée.'),
      })
    }
  }

  async function handleCreateObservation() {
    if (!observationTaskId) {
      return
    }
    if (!activeMembership?.id) {
      setFeedback({
        variant: 'error',
        message: 'Établissement non sélectionné.',
      })
      return
    }
    setFeedback(null)
    try {
      const response = await observationMutation.mutateAsync({
        taskExecutionId: observationTaskId,
        body: { text: observationDraft.text.trim() },
      })
      trackObservation({
        observationId: response.observation_id,
        establishmentId,
        authorMembershipId: activeMembership.id,
        origin: 'action_plan_task',
        submittedAt: new Date().toISOString(),
      })
      observationDraft.clear()
      setObservationTaskId(null)
      setFeedback({ variant: 'success', message: 'Observation créée.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'L’observation n’a pas pu être créée.'),
      })
    }
  }

  function handleTaskActionSelect(actionId: ActionPlanTaskActionId) {
    if (!taskActionsTask) {
      return
    }

    if (actionId === 'skip') {
      setSkipTaskId(taskActionsTask.id)
      return
    }

    setObservationTaskId(taskActionsTask.id)
  }

  return (
    <div className="flex min-h-full flex-col">
      {signalSummary ? (
        <ActionLinkedSignalStrip>
          <ActionLinkedSignalCard
            title={signalSummary.title}
            locationText={signalSummary.location_text || null}
            onPress={() => signalSummaryPath && navigate(signalSummaryPath)}
          />
        </ActionLinkedSignalStrip>
      ) : null}

      <div className="px-3 pt-2">
        <ActionDetailTabs activeTab={resolvedActiveTab} onChange={handleTabChange} />
      </div>

      <div
        className={cn(
          'mx-auto flex w-full flex-1 flex-col',
          'lg:max-w-7xl lg:px-6 lg:pt-4 lg:pb-6',
        )}
      >
        <div
          role="tabpanel"
          id="execution-detail-panel-details"
          aria-labelledby="execution-detail-tab-details"
          className={cn(
            'flex flex-col lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(20rem,24rem)] lg:items-start lg:gap-4',
            resolvedActiveTab !== 'details' && 'hidden',
          )}
        >
          <div
            className={cn(
              'flex flex-col gap-2.5 px-3 pt-2 lg:contents',
              showStickyFooter ? 'pb-40' : 'pb-4',
            )}
          >
            <div className="lg:col-span-2">
              <ActionPlanExecutionDetailHeader
                execution={execution}
                isOverdue={isOverdue}
                currentMembershipId={activeMembership?.id ?? null}
              />
            </div>

            {feedback ? (
              <div className="lg:col-span-2">
                <TerrainFeedback variant={feedback.variant} message={feedback.message} />
              </div>
            ) : null}

            <div className="flex flex-col gap-2.5 lg:col-start-1">
              {execution.task_executions.length === 0 ? (
                <TerrainEmptyState title="Aucune tâche dans cette exécution." />
              ) : (
                <>
                  <TerrainSectionLabel>Tâches par pôle</TerrainSectionLabel>
                  <ActionPlanExecutionDetailPoleSummarySection execution={execution} />
                  {poleSummaries.length > 1 ? (
                    <ActionPlanExecutionTaskFilters
                      poles={poleSummaries}
                      selectedPoleId={selectedPoleId}
                      onSelectedPoleIdChange={setSelectedPoleId}
                    />
                  ) : null}
                  {filteredTasks.length === 0 ? (
                    <TerrainEmptyState title="Aucune tâche pour ce pôle." />
                  ) : (
                    <ActionPlanExecutionTaskList
                      tasks={filteredTasks}
                      isTerminal={isTerminal}
                      isMutationPending={isMutationPending}
                      onMarkDone={handleTaskMarkDone}
                      onUnmarkDone={handleTaskMarkPending}
                      onOpenTaskActions={setTaskActionsTask}
                    />
                  )}
                </>
              )}
            </div>
          </div>

          {showStickyFooter ? (
            <ActionPlanExecutionStickyFooter
              ref={validationActionsRef}
              className="lg:col-start-2 lg:top-4 lg:bottom-auto lg:mt-0 lg:rounded-2xl lg:border lg:border-[#E8E6DF] lg:bg-white lg:p-4 lg:shadow-none"
              data-testid="execution-validation-actions"
              hints={permissionHints}
              isTerminal={isTerminal}
              isPending={isMutationPending}
              mutationErrorMessage={
                mutationError
                  ? resolveApiErrorMessage(mutationError, ActionPlansApiError, 'Action impossible.')
                  : null
              }
              onMarkDone={() => void handleMarkDone()}
              onValidate={() => void handleValidate()}
              onReopen={() => void handleReopen()}
              onCancel={() => void handleCancel()}
            />
          ) : null}
        </div>

        {hasOpenedComments ? (
          <div
            role="tabpanel"
            id="execution-detail-panel-comments"
            aria-labelledby="execution-detail-tab-comments"
            className={cn('px-3 pt-2 pb-4 lg:px-0 lg:pt-0', resolvedActiveTab !== 'comments' && 'hidden')}
          >
            <CommentSection
              establishmentId={establishmentId}
              targetType="action-plan-execution"
              targetId={executionId}
              highlightCommentId={highlightCommentId}
              readOnly={source === 'cross'}
            />
          </div>
        ) : null}
      </div>

      <ActionPlanExecutionTaskActionsSheet
        task={taskActionsTask}
        isTerminal={isTerminal}
        open={taskActionsTask != null}
        isPending={isMutationPending}
        onClose={() => setTaskActionsTask(null)}
        onSelectAction={handleTaskActionSelect}
      />

      <ActionPlanExecutionSkipSheet
        open={skipTaskId != null}
        isPending={skipMutation.isPending}
        onConfirm={() => skipTaskId && void handleSkip(skipTaskId)}
        onClose={() => setSkipTaskId(null)}
      />

      <ActionPlanExecutionObservationSheet
        open={observationTaskId != null}
        text={observationDraft.text}
        isPending={observationMutation.isPending}
        isOnline={isOnline}
        onTextChange={observationDraft.setText}
        onConfirm={() => void handleCreateObservation()}
        onClose={() => {
          setObservationTaskId(null)
        }}
      />

      <ActionPlanExecutionValidateRatingSheet
        open={isValidationSheetOpen}
        stars={validationStars}
        comment={validationComment}
        isPending={validateMutation.isPending}
        onStarsChange={setValidationStars}
        onCommentChange={setValidationComment}
        onConfirm={() => void handleValidateConfirm()}
        onClose={() => {
          if (validateMutation.isPending) {
            return
          }
          setIsValidationSheetOpen(false)
          setValidationStars(null)
          setValidationComment('')
        }}
      />
    </div>
  )
}

export function ActionPlanExecutionDetailPage({
  executionId,
  establishmentId: establishmentIdProp,
  source = 'establishment',
}: ActionPlanExecutionDetailPageProps) {
  const { activeMembership } = useAuth()
  const sessionEstablishmentId = activeMembership?.establishment_id ?? null
  const establishmentId = establishmentIdProp ?? sessionEstablishmentId

  const detailQuery = useActionPlanExecutionDetailQuery(establishmentId, executionId, { source })

  if (!establishmentId && source !== 'cross') {
    return null
  }

  if (detailQuery.isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 px-3 py-10 text-sm text-[#7D7B75]">
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
        Chargement de l&apos;exécution...
      </div>
    )
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message={resolveActionPlanErrorMessage(
          detailQuery.error,
          'Cette exécution est introuvable ou inaccessible.',
        )}
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  const resolvedEstablishmentId =
    detailQuery.data.establishment_id ?? establishmentId
  if (!resolvedEstablishmentId) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Cette exécution est introuvable ou inaccessible."
      />
    )
  }

  return (
    <ActionPlanExecutionDetailPageContent
      key={executionId}
      executionId={executionId}
      establishmentId={resolvedEstablishmentId}
      execution={detailQuery.data}
      source={source}
    />
  )
}
