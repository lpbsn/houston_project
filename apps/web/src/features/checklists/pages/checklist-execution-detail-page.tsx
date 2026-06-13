import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { ActionDeadlineProgressBar } from '@/components/domain/action-deadline-progress-bar'
import { TerrainCard, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { HoustonBadge } from '@/components/ui/terrain'
import { formatChecklistFeedBadgeLabel } from '@/features/checklists/lib/checklist-display'
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
  formatChecklistEndAtLabel,
  formatChecklistExecutionStatusLabel,
  formatChecklistProgressLabel,
  formatChecklistTaskStatusLabel,
  isChecklistExecutionOverdue,
} from '@/features/checklists/lib/checklist-display'
import {
  canShowChecklistExecutionCancel,
  canShowChecklistExecutionTaskActions,
} from '@/features/checklists/lib/checklist-execution-permission-hints'
import type { ChecklistTaskExecution } from '@/features/checklists/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

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
  const treatedCount = sortedTasks.filter((task) => task.status !== 'pending').length
  const isTerminal = execution.status === 'done' || execution.status === 'canceled'
  const endLabel = formatChecklistEndAtLabel(execution.end_at)
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
    <div className="space-y-3 px-3 pb-28 pt-3">
      <div className="flex flex-wrap items-center gap-2">
        <HoustonBadge variant="blue">
          {formatChecklistFeedBadgeLabel(execution.execution_source, null)}
        </HoustonBadge>
        <span className="rounded-full bg-[#F0EFE9] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[#7D7B75]">
          {formatChecklistExecutionStatusLabel(execution.status)}
        </span>
        {isOverdue ? <HoustonBadge variant="red">EN RETARD</HoustonBadge> : null}
      </div>

      <h1 className="text-xl font-bold text-[#1a1a1a]">{execution.template_title}</h1>
      {execution.template_description ? (
        <p className={cn('text-sm leading-6', terrain.muted)}>{execution.template_description}</p>
      ) : null}

      <TerrainCard className="space-y-2">
        <p className="text-sm font-semibold text-[#1a1a1a]">
          Progression : {formatChecklistProgressLabel(treatedCount, sortedTasks.length)}
        </p>
        {execution.end_at ? (
          <ActionDeadlineProgressBar
            createdAt={execution.created_at}
            dueAt={execution.end_at}
            isOverdue={isOverdue}
          />
        ) : null}
        {endLabel ? <p className={cn('text-xs', terrain.muted)}>Fin : {endLabel}</p> : null}
        <p className={cn('text-xs', terrain.muted)}>
          Assignée à {execution.assigned_to_display_name}
        </p>
        {execution.business_unit ? (
          <p className={cn('text-xs', terrain.muted)}>Pôle : {execution.business_unit.label}</p>
        ) : null}
      </TerrainCard>

      {feedback ? <ChecklistFeedback variant={feedback.variant} message={feedback.message} /> : null}

      <section className="space-y-2">
        <TerrainSectionLabel>Tâches</TerrainSectionLabel>
        <TerrainCard className="divide-y divide-[#F0EFE9] p-0">
          {sortedTasks.map((task, index) => (
            <div key={task.id} className="space-y-2 px-4 py-3.5">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-[#1a1a1a]">
                    {index + 1}. {task.task}
                  </p>
                </div>
                <span className="shrink-0 text-[10px] font-medium uppercase tracking-wide text-[#7D7B75]">
                  {formatChecklistTaskStatusLabel(task.status)}
                </span>
              </div>

              {canShowChecklistExecutionTaskActions(permissionHints, {
                isTerminal,
                task,
              }) ? (
                <div className="flex flex-col gap-2">
                  <Button
                    type="button"
                    size="sm"
                    className="rounded-lg bg-[#1B4FD8]"
                    disabled={markDoneMutation.isPending}
                    onClick={() => void handleMarkDone(task.id)}
                  >
                    Marquer terminée
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="rounded-lg border-[#E8E6DF]"
                    onClick={() => handleReportTask(task)}
                  >
                    Signaler
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="rounded-lg border-[#E8E6DF]"
                    onClick={() => {
                      setSkipTaskId(task.id)
                      setSkipReason('')
                    }}
                  >
                    Passer la tâche
                  </Button>
                </div>
              ) : null}

              {skipTaskId === task.id ? (
                <div className="space-y-2 rounded-xl border border-[#E8E6DF] bg-[#FAFAF8] p-3">
                  <Input
                    value={skipReason}
                    onChange={(e) => setSkipReason(e.target.value)}
                    placeholder="Raison (optionnel)"
                    className="h-10 border-[#E8E6DF] text-sm"
                  />
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="rounded-lg"
                      disabled={skipMutation.isPending}
                      onClick={() => void handleSkip(task.id)}
                    >
                      Confirmer
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="rounded-lg"
                      onClick={() => setSkipTaskId(null)}
                    >
                      Annuler
                    </Button>
                  </div>
                </div>
              ) : null}
            </div>
          ))}
        </TerrainCard>
      </section>

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

    </div>
  )
}
