import { LoaderCircle } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainEmptyState, TerrainErrorState } from '@/components/ui/terrain'
import {
  ActionDetailTabs,
  type ActionDetailTab,
} from '@/features/action-plans/components/action-detail-tabs'
import { ActionLinkedSignalCard } from '@/features/action-plans/components/action-linked-signal-card'
import { ActionLinkedSignalStrip } from '@/features/action-plans/components/action-linked-signal-strip'
import { CommentSection } from '@/features/comments/components/comment-section'
import {
  parseDetailDeepLink,
  readCurrentDetailDeepLink,
  useLocationSearch,
} from '@/features/comments/lib/detail-deep-link'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { cn } from '@/lib/utils'

import { ActionPlansApiError } from '../api'
import { ActionPlanExecutionDetailHeader } from '../components/action-plan-execution-detail-header'
import { ActionPlanExecutionObservationSheet } from '../components/action-plan-execution-observation-sheet'
import { ActionPlanExecutionSkipSheet } from '../components/action-plan-execution-skip-sheet'
import {
  ActionPlanExecutionTaskActionsSheet,
  type ActionPlanTaskActionId,
} from '../components/action-plan-execution-task-actions-sheet'
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
import {
  canShowActionPlanExecutionCancel,
} from '../lib/action-plan-permission-hints'
import type { ActionPlanExecutionDetail, ActionPlanTaskExecution } from '../types'

type ActionPlanExecutionDetailPageProps = {
  executionId: string
}

type ActionPlanExecutionDetailPageContentProps = {
  executionId: string
  establishmentId: string
  execution: ActionPlanExecutionDetail
}

function ActionPlanExecutionDetailPageContent({
  executionId,
  establishmentId,
  execution,
}: ActionPlanExecutionDetailPageContentProps) {
  const { navigate } = useAppRoute()
  const { activeMembership } = useAuth()
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

  const initialDeepLink = readCurrentDetailDeepLink()
  const locationSearch = useLocationSearch()
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
  const [observationText, setObservationText] = useState('')
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
      await markDoneMutation.mutateAsync()
      setFeedback({ variant: 'success', message: 'Plan marqué comme terminé.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être marqué terminé.'),
      })
    }
  }

  async function handleValidate() {
    setFeedback(null)
    try {
      await validateMutation.mutateAsync()
      setFeedback({ variant: 'success', message: 'Plan validé.' })
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
      setFeedback({ variant: 'success', message: 'Plan rouvert.' })
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
      setFeedback({ variant: 'success', message: 'Plan annulé.' })
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
    setFeedback(null)
    try {
      await observationMutation.mutateAsync({
        taskExecutionId: observationTaskId,
        body: { text: observationText.trim() },
      })
      setObservationTaskId(null)
      setObservationText('')
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
    setObservationText('')
  }

  return (
    <div className="flex min-h-full flex-col">
      {signalSummary ? (
        <ActionLinkedSignalStrip>
          <ActionLinkedSignalCard
            title={signalSummary.title}
            locationText={signalSummary.location_text || null}
            onPress={() => navigate(`/signals/${signalSummary.id}`)}
          />
        </ActionLinkedSignalStrip>
      ) : null}

      <div className="px-3 pt-2">
        <ActionDetailTabs activeTab={resolvedActiveTab} onChange={handleTabChange} />
      </div>

      <div
        className={cn(
          'flex flex-1 flex-col gap-2.5 px-3 pt-2',
          showStickyFooter ? 'pb-40' : 'pb-4',
        )}
      >
        <div
          role="tabpanel"
          id="execution-detail-panel-details"
          aria-labelledby="execution-detail-tab-details"
          className={cn('flex flex-col gap-2.5', resolvedActiveTab !== 'details' && 'hidden')}
        >
          <ActionPlanExecutionDetailHeader
            execution={execution}
            isOverdue={isOverdue}
            currentMembershipId={activeMembership?.id ?? null}
          />

          {feedback ? <TerrainFeedback variant={feedback.variant} message={feedback.message} /> : null}

          {execution.task_executions.length === 0 ? (
            <TerrainEmptyState title="Aucune tâche dans cette exécution." />
          ) : (
            <>
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

        {hasOpenedComments ? (
          <div
            role="tabpanel"
            id="execution-detail-panel-comments"
            aria-labelledby="execution-detail-tab-comments"
            className={cn(resolvedActiveTab !== 'comments' && 'hidden')}
          >
            <CommentSection
              establishmentId={establishmentId}
              targetType="action-plan-execution"
              targetId={executionId}
              highlightCommentId={highlightCommentId}
            />
          </div>
        ) : null}
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
        text={observationText}
        isPending={observationMutation.isPending}
        onTextChange={setObservationText}
        onConfirm={() => void handleCreateObservation()}
        onClose={() => {
          setObservationTaskId(null)
          setObservationText('')
        }}
      />
    </div>
  )
}

export function ActionPlanExecutionDetailPage({ executionId }: ActionPlanExecutionDetailPageProps) {
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  const detailQuery = useActionPlanExecutionDetailQuery(establishmentId, executionId)

  if (!establishmentId) {
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

  return (
    <ActionPlanExecutionDetailPageContent
      key={executionId}
      executionId={executionId}
      establishmentId={establishmentId}
      execution={detailQuery.data}
    />
  )
}
