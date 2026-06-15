import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainEmptyState, TerrainErrorState } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { ChecklistExecutionDetailHeader } from '@/features/checklists/components/checklist-execution-detail-header'
import { ChecklistExecutionSkipSheet } from '@/features/checklists/components/checklist-execution-skip-sheet'
import { ChecklistExecutionTaskRow } from '@/features/checklists/components/checklist-execution-task-row'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import {
  useCancelChecklistExecutionMutation,
  useChecklistExecutionDetailQuery,
  useMarkChecklistTaskDoneMutation,
  useSkipChecklistTaskMutation,
} from '@/features/checklists/hooks'
import { buildChecklistReportingHref } from '@/features/checklists/lib/checklist-reporting-context'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import {
  countChecklistTreatedTasks,
  isChecklistExecutionOverdue,
} from '@/features/checklists/lib/checklist-display'
import {
  canShowChecklistExecutionCancel,
  canShowChecklistExecutionTaskActions,
} from '@/features/checklists/lib/checklist-execution-permission-hints'
import type { ChecklistTaskExecution } from '@/features/checklists/types'

type ChecklistExecutionDetailPageProps = {
  executionId: string
}

export function ChecklistExecutionDetailPage({ executionId }: ChecklistExecutionDetailPageProps) {
  const { navigate } = useAppRoute()
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  const detailQuery = useChecklistExecutionDetailQuery(establishmentId, executionId)
  const cancelMutation = useCancelChecklistExecutionMutation(establishmentId ?? '', executionId)
  const markDoneMutation = useMarkChecklistTaskDoneMutation(establishmentId ?? '', executionId)
  const skipMutation = useSkipChecklistTaskMutation(establishmentId ?? '', executionId)
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )
  const [skipTaskId, setSkipTaskId] = useState<string | null>(null)
  const [skipReason, setSkipReason] = useState('')

  const isMutationPending = markDoneMutation.isPending || skipMutation.isPending

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
        message={resolveChecklistErrorMessage(
          detailQuery.error,
          'Cette exécution est introuvable ou inaccessible.',
        )}
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  const execution = detailQuery.data
  const sortedTasks = [...execution.task_executions].sort((a, b) => a.position - b.position)
  const treatedCount = countChecklistTreatedTasks(sortedTasks)
  const isTerminal = execution.status === 'done' || execution.status === 'canceled'
  const isOverdue = isChecklistExecutionOverdue(execution.end_at, isTerminal)
  const permissionHints = execution.permission_hints
  const showCancel = canShowChecklistExecutionCancel(permissionHints, { isTerminal })

  async function handleMarkDone(taskExecutionId: string) {
    setFeedback(null)
    try {
      await markDoneMutation.mutateAsync(taskExecutionId)
      setFeedback({ variant: 'success', message: 'Tâche terminée.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'La tâche n’a pas pu être terminée.'),
      })
    }
  }

  async function handleSkip(taskExecutionId: string) {
    setFeedback(null)
    try {
      await skipMutation.mutateAsync({
        taskExecutionId,
        body: skipReason.trim() ? { skipped_reason: skipReason.trim() } : {},
      })
      setSkipTaskId(null)
      setSkipReason('')
      setFeedback({ variant: 'success', message: 'Tâche passée.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'La tâche n’a pas pu être passée.'),
      })
    }
  }

  async function handleCancel() {
    setFeedback(null)
    try {
      await cancelMutation.mutateAsync()
      setFeedback({ variant: 'success', message: 'Exécution annulée.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'L’exécution n’a pas pu être annulée.'),
      })
    }
  }

  function handleReportTask(task: ChecklistTaskExecution) {
    navigate(
      buildChecklistReportingHref({
        checklistExecutionId: executionId,
        checklistTaskExecutionId: task.id,
      }),
    )
  }

  return (
    <div className="space-y-2 px-3 pb-28 pt-2">
      <ChecklistExecutionDetailHeader
        title={execution.template_title}
        businessUnitLabel={execution.business_unit?.label ?? null}
        endAt={execution.end_at}
        isOverdue={isOverdue}
        treatedCount={treatedCount}
        totalCount={sortedTasks.length}
      />

      {feedback ? <ChecklistFeedback variant={feedback.variant} message={feedback.message} /> : null}

      {sortedTasks.length === 0 ? (
        <TerrainEmptyState title="Aucune tâche dans cette exécution." />
      ) : (
        <div className="space-y-2">
          {sortedTasks.map((task) => (
            <ChecklistExecutionTaskRow
              key={task.id}
              task={task}
              canShowActions={canShowChecklistExecutionTaskActions(permissionHints, {
                isTerminal,
                task,
              })}
              isMutationPending={isMutationPending}
              onMarkDone={() => void handleMarkDone(task.id)}
              onReport={() => handleReportTask(task)}
              onSkipRequest={() => {
                setSkipTaskId(task.id)
                setSkipReason('')
              }}
            />
          ))}
        </div>
      )}

      {showCancel ? (
        <Button
          type="button"
          variant="outline"
          className="h-11 w-full rounded-xl border-[#E8E6DF] text-[#E24B4A]"
          disabled={cancelMutation.isPending}
          onClick={() => void handleCancel()}
        >
          Annuler l&apos;exécution
        </Button>
      ) : null}

      <ChecklistExecutionSkipSheet
        open={skipTaskId !== null}
        skipReason={skipReason}
        isPending={skipMutation.isPending}
        onSkipReasonChange={setSkipReason}
        onConfirm={() => {
          if (skipTaskId) {
            void handleSkip(skipTaskId)
          }
        }}
        onClose={() => {
          setSkipTaskId(null)
          setSkipReason('')
        }}
      />
    </div>
  )
}
