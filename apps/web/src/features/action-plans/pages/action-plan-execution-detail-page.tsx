import { LoaderCircle } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { serializeScopedSignalDetailPath } from '@/app/scoped-terrain'
import { useAuth } from '@/app/auth-provider'
import { TerrainDetailTrailingSlot } from '@/components/layout/terrain-detail-trailing-slot'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { useLgViewport } from '@/lib/lg-viewport'
import { TerrainCard, TerrainEmptyState, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
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
import { resyncBootstrapAfterLegalError } from '@/features/auth/api'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE, readAiConsentStatus } from '@/lib/legal'
import { useNetworkStatus } from '@/lib/network-status'
import { notifySuccess } from '@/lib/success-toast'

import { ActionPlansApiError } from '../api'
import { ActionPlanExecutionDetailContextCard } from '../components/action-plan-execution-detail-context-card'
import { ActionPlanExecutionDetailDeadlineSection } from '../components/action-plan-execution-detail-deadline-section'
import { ActionPlanExecutionDetailHeader } from '../components/action-plan-execution-detail-header'
import { ActionPlanExecutionDetailLabel } from '../components/action-plan-execution-detail-label'
import { ActionPlanExecutionDetailPoleSummarySection } from '../components/action-plan-execution-detail-pole-summary-section'
import { ActionPlanExecutionDetailReviewSection } from '../components/action-plan-execution-detail-review-section'
import { ActionPlanExecutionObservationSheet } from '../components/action-plan-execution-observation-sheet'
import { ActionPlanExecutionSkipSheet } from '../components/action-plan-execution-skip-sheet'
import {
  ActionPlanExecutionTaskActionsSheet,
  type ActionPlanTaskActionId,
} from '../components/action-plan-execution-task-actions-sheet'
import { ActionPlanExecutionValidateRatingSheet } from '../components/action-plan-execution-validate-rating-sheet'
import { ActionPlanExecutionLifecycleActions } from '../components/action-plan-execution-lifecycle-actions'
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
  isActionPlanTaskPending,
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
  const { activeMembership, user, bootstrap } = useAuth()
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const aiConsentGranted = readAiConsentStatus(user ?? bootstrap?.user) === 'granted'
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
  const commentsAnchorRef = useRef<HTMLElement>(null)
  const shouldScrollToComments =
    isDesktopWeb && (initialDeepLink.tab === 'comments' || highlightCommentId != null)
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
  const taskStatusCommandInFlightRef = useRef(false)

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
  const showStickyFooter =
    !isDesktopWeb && resolvedActiveTab === 'details' && canShowLifecycleFooter
  const shouldScrollToValidationActions =
    shouldFocusValidation && resolvedActiveTab === 'details' && permissionHints.can_validate

  useEffect(() => {
    if (!shouldScrollToValidationActions) {
      return
    }

    validationActionsRef.current?.scrollIntoView({ block: 'end' })
  }, [shouldScrollToValidationActions])

  useEffect(() => {
    if (!shouldScrollToComments) {
      return
    }
    commentsAnchorRef.current?.scrollIntoView({ block: 'start' })
  }, [shouldScrollToComments])

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

  function reportInlineSuccess(message: string) {
    if (isDesktopWeb) {
      return
    }
    setFeedback({ variant: 'success', message })
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
    if (taskStatusCommandInFlightRef.current) {
      return
    }
    taskStatusCommandInFlightRef.current = true
    setFeedback(null)
    try {
      await markTaskDoneMutation.mutateAsync(taskExecutionId)
      reportInlineSuccess('Tâche terminée.')
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'La tâche n’a pas pu être terminée.'),
      })
    } finally {
      taskStatusCommandInFlightRef.current = false
    }
  }

  async function handleTaskMarkPending(taskExecutionId: string) {
    if (taskStatusCommandInFlightRef.current) {
      return
    }
    taskStatusCommandInFlightRef.current = true
    setFeedback(null)
    try {
      await markTaskPendingMutation.mutateAsync(taskExecutionId)
      reportInlineSuccess('Tâche remise en cours.')
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'La tâche n’a pas pu être remise en cours.'),
      })
    } finally {
      taskStatusCommandInFlightRef.current = false
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
      reportInlineSuccess('Tâche passée.')
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
    if (!aiConsentGranted) {
      setFeedback({
        variant: 'error',
        message: OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE,
      })
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
      reportInlineSuccess('Observation créée.')
    } catch (error) {
      const resynced = await resyncBootstrapAfterLegalError(error)
      setFeedback({
        variant: 'error',
        message:
          readAiConsentStatus(resynced?.user ?? user ?? bootstrap?.user) === 'declined'
            ? OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE
            : resolveActionPlanErrorMessage(error, 'L’observation n’a pas pu être créée.'),
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

    if (!aiConsentGranted) {
      setTaskActionsTask(null)
      setFeedback({
        variant: 'error',
        message: OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE,
      })
      return
    }
    setObservationTaskId(taskActionsTask.id)
  }

  const linkedSignal = signalSummary ? (
    <ActionLinkedSignalCard
      title={signalSummary.title}
      locationText={signalSummary.location_text || null}
      onPress={() => signalSummaryPath && navigate(signalSummaryPath)}
    />
  ) : null
  const commentSection = (
    <CommentSection
      establishmentId={establishmentId}
      targetType="action-plan-execution"
      targetId={executionId}
      highlightCommentId={highlightCommentId}
      readOnly={source === 'cross'}
      documentFlow={isDesktopWeb}
      documentFlowTitle={
        isDesktopWeb ? (
          <ActionPlanExecutionDetailLabel>Commentaires</ActionPlanExecutionDetailLabel>
        ) : undefined
      }
      pinComposer={!isDesktopWeb}
      attachTrigger={isDesktopWeb ? 'icon' : 'label'}
      attachEnabled={
        source !== 'cross' &&
        (execution.status === 'in_progress' || execution.status === 'pending_validation')
      }
    />
  )
  const taskTotal = execution.task_executions.length
  const taskTreated = execution.task_executions.filter(
    (task) => !isActionPlanTaskPending(task),
  ).length
  const taskZoneBody = (
    <>
      {isDesktopWeb ? null : <ActionPlanExecutionDetailPoleSummarySection execution={execution} />}
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
            density={isDesktopWeb ? 'compact' : 'default'}
            onMarkDone={handleTaskMarkDone}
            onUnmarkDone={handleTaskMarkPending}
            onOpenTaskActions={setTaskActionsTask}
          />
      )}
    </>
  )
  const taskZone =
    taskTotal === 0 ? (
      <TerrainEmptyState title="Aucune tâche dans cette exécution." />
    ) : isDesktopWeb ? (
      <section className="rounded-xl border border-[#E8E6DF] bg-[#FAFAF8] px-3 py-3">
        <div className="mb-2 flex items-baseline justify-between gap-3">
          <ActionPlanExecutionDetailLabel className="text-[#7D7B75]">
            Tâches par pôle
          </ActionPlanExecutionDetailLabel>
          <span className="shrink-0 text-[12px] tabular-nums text-[#7D7B75]">
            {taskTreated}/{taskTotal}
          </span>
        </div>
        {taskZoneBody}
      </section>
    ) : (
      <>
        <TerrainSectionLabel>Tâches par pôle</TerrainSectionLabel>
        {taskZoneBody}
      </>
    )
  const executionHeader = (
    <ActionPlanExecutionDetailHeader
      execution={execution}
      isOverdue={isOverdue}
      currentMembershipId={activeMembership?.id ?? null}
    />
  )
  const lifecycleActions = canShowLifecycleFooter ? (
    <ActionPlanExecutionLifecycleActions
      hints={permissionHints}
      isTerminal={isTerminal}
      isPending={isMutationPending}
      layout="page"
      onMarkDone={() => void handleMarkDone()}
      onValidate={() => void handleValidate()}
      onReopen={() => void handleReopen()}
      onCancel={() => void handleCancel()}
    />
  ) : null

  return (
    <div className="flex min-h-full flex-col">
      {isDesktopWeb || !signalSummary ? null : (
        <ActionLinkedSignalStrip>{linkedSignal}</ActionLinkedSignalStrip>
      )}

      <div
        data-testid="execution-detail-frame"
        className="flex w-full flex-1 flex-col"
      >
      {isDesktopWeb ? (
        <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 pt-4 pb-8">
          <TerrainDetailTrailingSlot>
            {canShowLifecycleFooter ? (
              <div
                ref={validationActionsRef}
                data-testid="execution-detail-page-actions"
                className="flex min-w-0 flex-wrap items-center justify-end gap-2"
              >
                {mutationError ? (
                  <p className="text-sm text-destructive" role="alert">
                    {resolveApiErrorMessage(mutationError, ActionPlansApiError, 'Action impossible.')}
                  </p>
                ) : null}
                {lifecycleActions}
              </div>
            ) : null}
          </TerrainDetailTrailingSlot>
          {feedback && feedback.variant === 'error' ? (
            <TerrainFeedback variant={feedback.variant} message={feedback.message} />
          ) : null}
          <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
            <div
              data-testid="execution-detail-main"
              className="flex min-w-0 flex-col gap-4 xl:col-start-1 xl:row-start-1"
            >
              <TerrainCard>
                <ActionPlanExecutionDetailLabel>Titre</ActionPlanExecutionDetailLabel>
                <h1 className="mt-2 text-[13px] font-normal leading-relaxed text-[#1a1a1a]">
                  {execution.title}
                </h1>
              </TerrainCard>
              <TerrainCard>
                <ActionPlanExecutionDetailLabel>Description</ActionPlanExecutionDetailLabel>
                <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-[#1a1a1a]">
                  {execution.description.trim() || 'Aucune description.'}
                </p>
              </TerrainCard>
              {taskZone}
            </div>
            <div
              data-testid="execution-detail-context"
              className="flex min-w-0 flex-col gap-4 self-start xl:col-start-2 xl:row-start-1 xl:row-span-2"
            >
              <ActionPlanExecutionDetailContextCard
                execution={execution}
                currentMembershipId={activeMembership?.id ?? null}
              />
              <ActionPlanExecutionDetailDeadlineSection
                execution={execution}
                isOverdue={isOverdue}
                isTerminal={isTerminal}
                variant="planification"
              />
              {execution.active_review != null ? (
                <ActionPlanExecutionDetailReviewSection activeReview={execution.active_review} />
              ) : null}
              {linkedSignal}
            </div>
            <section
              ref={commentsAnchorRef}
              id="execution-detail-comments"
              aria-label="Commentaires"
              data-testid="execution-detail-comments-section"
              className="flex scroll-mt-4 flex-col xl:col-start-1 xl:row-start-2"
            >
              <TerrainCard>{commentSection}</TerrainCard>
            </section>
          </div>
        </div>
      ) : (
        <>
      <div data-testid="execution-detail-tab-bar" className="px-3 pt-2">
        <ActionDetailTabs activeTab={resolvedActiveTab} onChange={handleTabChange} />
      </div>

      <div className="flex w-full flex-1 flex-col">
        <div
          role="tabpanel"
          id="execution-detail-panel-details"
          aria-labelledby="execution-detail-tab-details"
          data-testid="execution-detail-details-panel"
          className={resolvedActiveTab === 'details' ? 'flex min-h-full flex-col' : 'hidden'}
        >
          <div
            data-testid="execution-detail-details-content"
            className="flex flex-col gap-2.5 px-3 pt-2 pb-4"
          >
            {executionHeader}
            {feedback ? (
              <TerrainFeedback variant={feedback.variant} message={feedback.message} />
            ) : null}
            {taskZone}
          </div>

          {showStickyFooter ? (
            <ActionPlanExecutionStickyFooter
              ref={validationActionsRef}
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
            data-testid="execution-detail-comments-panel"
            className={
              resolvedActiveTab === 'comments'
                ? 'flex min-h-0 flex-1 flex-col px-3 pt-2 pb-4'
                : 'hidden'
            }
          >
            {commentSection}
          </div>
        ) : null}
      </div>
        </>
      )}
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
